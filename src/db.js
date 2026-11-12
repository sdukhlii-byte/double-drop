'use strict';

const fs = require('fs');
const path = require('path');
const Database = require('better-sqlite3');

function openDb(dataDir) {
  // Fall back to ./data when the volume is not mounted (local runs)
  let dir = dataDir;
  try {
    fs.mkdirSync(dir, { recursive: true });
    fs.accessSync(dir, fs.constants.W_OK);
  } catch {
    dir = path.join(process.cwd(), 'data');
    fs.mkdirSync(dir, { recursive: true });
  }

  const db = new Database(path.join(dir, 'bot.sqlite'));
  db.pragma('journal_mode = WAL');

  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      telegram_id INTEGER PRIMARY KEY,
      username    TEXT,
      first_name  TEXT,
      lang        TEXT,
      start_param TEXT,
      created_at  INTEGER NOT NULL,
      last_start  INTEGER NOT NULL,
      blocked     INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS clicks (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      telegram_id INTEGER NOT NULL,
      kind        TEXT NOT NULL,
      created_at  INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_clicks_user ON clicks(telegram_id);
    CREATE TABLE IF NOT EXISTS events (
      id          INTEGER PRIMARY KEY AUTOINCREMENT,
      telegram_id INTEGER NOT NULL,
      event       TEXT NOT NULL,
      payload     TEXT,
      created_at  INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_events_user ON events(telegram_id);
    CREATE TABLE IF NOT EXISTS pushes (
      telegram_id INTEGER NOT NULL,
      push_id     TEXT NOT NULL,
      status      TEXT NOT NULL,
      sent_at     INTEGER,
      error       TEXT,
      PRIMARY KEY (telegram_id, push_id)
    );
    CREATE TABLE IF NOT EXISTS kv (
      key   TEXT PRIMARY KEY,
      value TEXT
    );
  `);

  const now = () => Date.now();

  const q = {
    upsertUser: db.prepare(`
      INSERT INTO users (telegram_id, username, first_name, lang, start_param, created_at, last_start)
      VALUES (@telegram_id, @username, @first_name, @lang, @start_param, @t, @t)
      ON CONFLICT(telegram_id) DO UPDATE SET
        username = excluded.username,
        first_name = excluded.first_name,
        lang = excluded.lang,
        last_start = excluded.last_start,
        blocked = 0,
        start_param = COALESCE(users.start_param, excluded.start_param)
    `),
    addClick: db.prepare('INSERT INTO clicks (telegram_id, kind, created_at) VALUES (?, ?, ?)'),
    addEvent: db.prepare('INSERT INTO events (telegram_id, event, payload, created_at) VALUES (?, ?, ?, ?)'),
    markBlocked: db.prepare('UPDATE users SET blocked = 1 WHERE telegram_id = ?'),
    getKv: db.prepare('SELECT value FROM kv WHERE key = ?'),
    setKv: db.prepare('INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value'),
    countUsers: db.prepare('SELECT COUNT(*) AS n FROM users'),
    countBlocked: db.prepare('SELECT COUNT(*) AS n FROM users WHERE blocked = 1'),
    countClicks: db.prepare('SELECT kind, COUNT(*) AS n, COUNT(DISTINCT telegram_id) AS u FROM clicks GROUP BY kind'),
    countEvents: db.prepare('SELECT event, COUNT(*) AS n, COUNT(DISTINCT telegram_id) AS u FROM events GROUP BY event'),
    claimPush: db.prepare("INSERT OR IGNORE INTO pushes (telegram_id, push_id, status) VALUES (?, ?, 'claimed')"),
    finishPush: db.prepare('UPDATE pushes SET status = ?, sent_at = ?, error = ? WHERE telegram_id = ? AND push_id = ?'),
    pushStats: db.prepare('SELECT push_id, status, COUNT(*) AS n FROM pushes GROUP BY push_id, status ORDER BY push_id'),
    // Stage "reg": user has not registered yet. Counted from the first /start.
    dueReg: db.prepare(`
      SELECT u.telegram_id AS id FROM users u
      WHERE u.blocked = 0
        AND NOT EXISTS (SELECT 1 FROM events e WHERE e.telegram_id = u.telegram_id AND e.event IN ('reg', 'ftd'))
        AND NOT EXISTS (SELECT 1 FROM pushes p WHERE p.telegram_id = u.telegram_id AND p.push_id = @pushId)
        AND NOT EXISTS (SELECT 1 FROM pushes g WHERE g.telegram_id = u.telegram_id AND g.sent_at > @now - @gap)
        AND u.created_at + @delay <= @now
        AND u.created_at + @delay + @late > @now
      ORDER BY u.created_at LIMIT @limit
    `),
    // Stage "dep": registered (postback "reg") but no deposit yet. Counted from the registration postback.
    dueDep: db.prepare(`
      SELECT u.telegram_id AS id FROM users u
      JOIN (SELECT telegram_id, MIN(created_at) AS reg_at FROM events WHERE event = 'reg' GROUP BY telegram_id) r
        ON r.telegram_id = u.telegram_id
      WHERE u.blocked = 0
        AND NOT EXISTS (SELECT 1 FROM events e WHERE e.telegram_id = u.telegram_id AND e.event = 'ftd')
        AND NOT EXISTS (SELECT 1 FROM pushes p WHERE p.telegram_id = u.telegram_id AND p.push_id = @pushId)
        AND NOT EXISTS (SELECT 1 FROM pushes g WHERE g.telegram_id = u.telegram_id AND g.sent_at > @now - @gap)
        AND r.reg_at + @delay <= @now
        AND r.reg_at + @delay + @late > @now
      ORDER BY r.reg_at LIMIT @limit
    `),
    topSources: db.prepare(`
      SELECT COALESCE(start_param, '(none)') AS src, COUNT(*) AS n
      FROM users GROUP BY src ORDER BY n DESC LIMIT 10
    `),
  };

  return {
    raw: db,
    saveUser(u, startParam) {
      q.upsertUser.run({
        telegram_id: u.id,
        username: u.username || null,
        first_name: u.first_name || null,
        lang: u.language_code || null,
        start_param: startParam || null,
        t: now(),
      });
    },
    addClick(telegramId, kind) {
      q.addClick.run(telegramId, kind, now());
    },
    addEvent(telegramId, event, payload) {
      q.addEvent.run(telegramId, event, payload ? JSON.stringify(payload) : null, now());
    },
    markBlocked(telegramId) {
      q.markBlocked.run(telegramId);
    },
    getKv(key) {
      const r = q.getKv.get(key);
      return r ? r.value : null;
    },
    setKv(key, value) {
      q.setKv.run(key, value);
    },
    // Atomically reserve a push for a user (false = already reserved/sent, never send twice)
    claimPush(telegramId, pushId) {
      return q.claimPush.run(telegramId, pushId).changes === 1;
    },
    finishPush(telegramId, pushId, status, error, at = now()) {
      q.finishPush.run(status, status === 'sent' ? at : null, error ? String(error).slice(0, 200) : null, telegramId, pushId);
    },
    duePush({ pushId, stage, delayMs, lateMs, gapMs = 0, now: t, limit = 100 }) {
      const args = { pushId, delay: delayMs, late: lateMs, gap: gapMs, now: t, limit };
      const rows = stage === 'dep' ? q.dueDep.all(args) : q.dueReg.all(args);
      return rows.map((r) => r.id);
    },
    stats() {
      return {
        users: q.countUsers.get().n,
        blocked: q.countBlocked.get().n,
        clicks: q.countClicks.all(),
        events: q.countEvents.all(),
        sources: q.topSources.all(),
        pushes: q.pushStats.all(),
      };
    },
  };
}

module.exports = { openDb };
