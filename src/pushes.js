'use strict';

const fs = require('fs');
const path = require('path');
const { Input } = require('telegraf');
const { buildPushKeyboard } = require('./keyboard');

const CAPTION_LIMIT = 1024;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function loadPushes(cfg) {
  const list = JSON.parse(fs.readFileSync(path.join(cfg.offerDir, 'pushes.json'), 'utf8'));
  return list.map((p) => {
    const html = fs.readFileSync(path.join(cfg.offerDir, p.text), 'utf8').trim();
    if (html.includes('[[')) console.warn(`[push:${p.id}] text still contains [[placeholders]]`);
    if (html.length > CAPTION_LIMIT) console.warn(`[push:${p.id}] text is ${html.length} chars, photo caption limit is ${CAPTION_LIMIT}`);
    if (!['reg', 'dep'].includes(p.stage)) throw new Error(`push ${p.id}: stage must be "reg" or "dep"`);
    return { ...p, html, imagePath: path.join(cfg.assetsDir, p.image), buttons: p.buttons || ['play', 'community'] };
  });
}

/**
 * Push sequence after /start. The first push is sent `delayMinutes` after the user's first /start,
 * every next push `delayMinutes` after the previous one. Stops for users who blocked the bot
 * or whose Coinplay postback confirmed a first deposit (event "ftd").
 */
function createPushScheduler({ cfg, db, telegram, pushes = loadPushes(cfg) }) {
  const lateMs = cfg.pushMaxLateMin * 60 * 1000;
  const gapMs = (cfg.pushMinGapMin || 0) * 60 * 1000;
  let timer = null;
  let running = false;

  async function sendNow(push, userId) {
    const keyboard = buildPushKeyboard(cfg, userId, push.buttons);
    const cacheKey = `push_img_${push.image}_file_id`;
    const cached = db.getKv(cacheKey);
    const extra = { caption: push.html, parse_mode: 'HTML', reply_markup: keyboard };

    let msg;
    try {
      msg = await telegram.sendPhoto(userId, cached || Input.fromLocalFile(push.imagePath), extra);
    } catch (err) {
      const code = err && err.response && err.response.error_code;
      if (cached && code === 400) {
        // Cached file_id is dead (e.g. token re-issued): upload the file again
        db.setKv(cacheKey, '');
        msg = await telegram.sendPhoto(userId, Input.fromLocalFile(push.imagePath), extra);
      } else {
        throw err;
      }
    }
    if (!cached && msg && msg.photo && msg.photo.length) {
      db.setKv(cacheKey, msg.photo[msg.photo.length - 1].file_id);
    }
    return msg;
  }

  async function tick(now = Date.now()) {
    if (running) return 0;
    running = true;
    let sent = 0;
    const servedNow = new Set(); // at most one push per user per tick
    try {
      // Stage order: deposit pushes first (closer to money), then registration pushes
      const ordered = [...pushes.filter((p) => p.stage === 'dep'), ...pushes.filter((p) => p.stage === 'reg')];
      for (const push of ordered) {
        const due = db.duePush({
          pushId: push.id,
          stage: push.stage,
          delayMs: push.delayMinutes * 60 * 1000,
          lateMs,
          gapMs,
          now,
        });
        for (const userId of due) {
          if (servedNow.has(userId)) continue;
          if (!db.claimPush(userId, push.id)) continue; // reserved first, so a crash never causes a double send
          servedNow.add(userId);
          try {
            await sendNow(push, userId);
            db.finishPush(userId, push.id, 'sent', null, now);
            sent++;
          } catch (err) {
            const code = err && err.response && err.response.error_code;
            if (code === 403) db.markBlocked(userId);
            db.finishPush(userId, push.id, 'failed', err.message);
            console.error(`[push:${push.id}] user ${userId}: ${err.message}`);
          }
          await sleep(40); // stay well under Telegram's ~30 msg/s limit
        }
      }
    } finally {
      running = false;
    }
    return sent;
  }

  return {
    pushes,
    sendNow,
    tick,
    start(intervalMs = 30000) {
      if (timer) return;
      timer = setInterval(() => tick().catch((e) => console.error('[push] tick failed:', e.message)), intervalMs);
      console.log(`[push] scheduler on: ${pushes.map((p) => `${p.id} [${p.stage} +${p.delayMinutes}m]`).join(', ')}`);
    },
    stop() {
      if (timer) clearInterval(timer);
      timer = null;
    },
  };
}

module.exports = { createPushScheduler, loadPushes };
