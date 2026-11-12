'use strict';

const test = require('node:test');
const assert = require('node:assert');
const os = require('os');
const path = require('path');
const fs = require('fs');

process.env.BOT_TOKEN = 'test';
process.env.COINPLAY_LINK = 'https://coinplay.example/aff?a=1';
process.env.PUBLIC_URL = 'https://bot.example';

const config = require('../src/config');
const { openDb } = require('../src/db');
const { createPushScheduler, loadPushes } = require('../src/pushes');

const MIN = 60 * 1000;

function setup() {
  const db = openDb(fs.mkdtempSync(path.join(os.tmpdir(), 'cppush-')));
  const sent = [];
  const telegram = {
    async sendPhoto(userId, photo, extra) {
      sent.push({ userId, photo, extra });
      return { message_id: 1, photo: [{ file_id: 'S' }, { file_id: `FILE_${sent.length}` }] };
    },
  };
  const scheduler = createPushScheduler({ cfg: { ...config, pushMaxLateMin: 180 }, db, telegram });
  const addUser = (id, startedAgoMin, now) => {
    db.saveUser({ id, first_name: 'T' }, null);
    db.raw.prepare('UPDATE users SET created_at = ? WHERE telegram_id = ?').run(now - startedAgoMin * MIN, id);
  };
  return { db, sent, scheduler, addUser };
}

test('push files: real text, images exist, caption fits, no "free", no placeholders', () => {
  for (const p of loadPushes(config)) {
    assert.ok(fs.existsSync(p.imagePath), `${p.id}: image exists`);
    assert.ok(p.html.length <= 1024);
    assert.ok(!p.html.includes('[['));
    assert.ok(!/free/i.test(p.html));
  }
});

const ids = (sent) => sent.map((x) => x.extra.caption.slice(0, 12));

test('reg stage: pushes at +20 min, +90 min, +6 h, +24 h, +48 h, each once', async () => {
  const { sent, scheduler, addUser } = setup();
  const t0 = 1_000_000_000_000;
  addUser(1, 0, t0);
  const at = (min) => scheduler.tick(t0 + min * MIN);

  assert.strictEqual(await at(10), 0, 'too early');
  assert.strictEqual(await at(21), 1, 'reg1');
  assert.strictEqual(await at(22), 0);
  assert.strictEqual(await at(91), 1, 'reg2');
  assert.strictEqual(await at(95), 0, 'nothing twice');
  assert.strictEqual(await at(361), 1, 'reg3');
  assert.strictEqual(await at(1441), 1, 'reg4');
  assert.strictEqual(await at(2881), 1, 'reg5');
  assert.strictEqual(await at(5000), 0, 'sequence finished');
  assert.strictEqual(sent.length, 5);
  assert.ok(sent[0].extra.caption.includes('make your choice'));
  const kb = sent[0].extra.reply_markup.inline_keyboard;
  assert.strictEqual(kb[0][0].web_app.url, 'https://bot.example/r?c=1&m=app');
  assert.strictEqual(kb[0][0].style, 'primary');
  assert.strictEqual(kb[1][0].text, 'Join community!');
});

test('registration postback switches the user from reg pushes to deposit pushes', async () => {
  const { db, sent, scheduler, addUser } = setup();
  const t0 = 2_000_000_000_000;
  addUser(5, 0, t0);
  assert.strictEqual(await scheduler.tick(t0 + 21 * MIN), 1, 'reg1 sent');

  // user registers at +30 min
  db.addEvent(5, 'reg', {});
  db.raw.prepare("UPDATE events SET created_at = ? WHERE event = 'reg'").run(t0 + 30 * MIN);

  // at +95 min reg2 (+90) would be due, but the user registered: they get dep1 (reg +15) instead
  assert.strictEqual(await scheduler.tick(t0 + 95 * MIN), 1);
  assert.ok(sent[1].extra.caption.includes("You're in"));
  assert.strictEqual(await scheduler.tick(t0 + 300 * MIN), 1, 'dep2 (reg +3 h), never reg3');
  assert.ok(sent[2].extra.caption.includes('40+ coins, one account'));
});

test('dep pushes: +15 min, +3 h, +24 h, +72 h after reg; stop at FTD', async () => {
  const { db, sent, scheduler, addUser } = setup();
  const t0 = 3_000_000_000_000;
  addUser(6, 0, t0);
  db.addEvent(6, 'reg', {});
  db.raw.prepare("UPDATE events SET created_at = ? WHERE event = 'reg'").run(t0);
  const at = (min) => scheduler.tick(t0 + min * MIN);

  assert.strictEqual(await at(10), 0);
  assert.strictEqual(await at(16), 1, 'dep1');
  assert.ok(sent[0].extra.caption.includes("You're in"));
  assert.strictEqual(await at(181), 1, 'dep2');
  db.addEvent(6, 'ftd', {});
  assert.strictEqual(await at(1441), 0, 'no more pushes after the deposit');
  assert.strictEqual(sent.length, 2);
});

test('min gap: two overdue pushes are not sent back to back', async () => {
  const { sent, scheduler, addUser } = setup();
  const t0 = 4_000_000_000_000;
  addUser(7, 0, t0);
  // downtime: at +100 min both reg1 (+20) and reg2 (+90) are due
  assert.strictEqual(await scheduler.tick(t0 + 100 * MIN), 1);
  assert.strictEqual(await scheduler.tick(t0 + 101 * MIN), 0, 'gap of 30 min');
  assert.strictEqual(await scheduler.tick(t0 + 135 * MIN), 1, 'reg2 still inside its late window');
  assert.strictEqual(sent.length, 2);
});

test('skips FTD users, blocked users and pushes overdue past the window', async () => {
  const { db, sent, scheduler, addUser } = setup();
  const t0 = 5_000_000_000_000;
  addUser(10, 25, t0); // FTD user
  addUser(11, 25, t0); // blocked user
  addUser(12, 24 * 60 + 1, t0); // reg1..reg3 long overdue, reg4 (+24h) is due now
  addUser(13, 25, t0); // normal user
  db.addEvent(10, 'ftd', {});
  db.markBlocked(11);

  await scheduler.tick(t0);
  const got = sent.map((s) => s.userId).sort();
  assert.deepStrictEqual(got, [12, 13]);
  assert.ok(sent.find((s) => s.userId === 12).extra.caption.includes('Match day'), 'only the push whose window is open');
});

test('image file_id is cached by image and reused for other users', async () => {
  const { db, sent, scheduler, addUser } = setup();
  const t0 = 6_000_000_000_000;
  addUser(20, 30, t0);
  addUser(21, 30, t0);
  await scheduler.tick(t0);
  assert.strictEqual(typeof sent[0].photo, 'object', 'first user: file upload');
  assert.strictEqual(sent[1].photo, db.getKv('push_img_push1.jpg_file_id'), 'second user: cached file_id');
});
