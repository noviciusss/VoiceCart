CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS items (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  TEXT        NOT NULL,
  name        TEXT        NOT NULL,
  category    TEXT        DEFAULT 'other',
  quantity    INT         DEFAULT 1,
  unit        TEXT        DEFAULT '',
  status      TEXT        DEFAULT 'active',   -- active | purchased
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS history (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  TEXT        NOT NULL,
  item_name   TEXT        NOT NULL,
  category    TEXT        DEFAULT 'other',
  event       TEXT        NOT NULL,            -- added | purchased | removed
  timestamp   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_items_session   ON items(session_id, status);
CREATE INDEX IF NOT EXISTS idx_history_session ON history(session_id);
