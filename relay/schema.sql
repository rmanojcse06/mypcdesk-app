-- MyDesk WhatsApp relay: messages waiting for MyDesk to collect.
CREATE TABLE IF NOT EXISTS messages (
  id          TEXT PRIMARY KEY,   -- WhatsApp message id (so a retried webhook is stored once)
  from_number TEXT NOT NULL,
  body        TEXT NOT NULL,
  ts          REAL NOT NULL,      -- seconds since 1970, from WhatsApp
  taken       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS messages_waiting ON messages (taken, ts);
