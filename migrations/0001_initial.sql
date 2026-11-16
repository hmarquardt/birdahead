PRAGMA foreign_keys = ON;
-- Household learners. Access keys live only in Worker secrets.
CREATE TABLE IF NOT EXISTS profiles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL
);
INSERT OR IGNORE INTO profiles(id,name) VALUES ('hank','Hank'),('heather','Heather');

-- Opaque session tokens; only SHA-256 hashes are stored.
CREATE TABLE IF NOT EXISTS auth_sessions (
  token_hash TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL REFERENCES profiles(id),
  expires_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS auth_sessions_expiry ON auth_sessions(expires_at);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL REFERENCES profiles(id),
  release_id TEXT NOT NULL,
  release_family TEXT NOT NULL,
  location TEXT NOT NULL,
  outing_day TEXT NOT NULL,
  kind TEXT NOT NULL,
  mode TEXT NOT NULL,
  started TEXT NOT NULL,
  questions TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_profile_started ON sessions(profile_id, started);

CREATE TABLE IF NOT EXISTS attempts (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  question_id TEXT UNIQUE NOT NULL,
  profile_id TEXT NOT NULL REFERENCES profiles(id),
  asset_id TEXT NOT NULL,
  species_code TEXT NOT NULL,
  kind TEXT NOT NULL,
  mode TEXT NOT NULL,
  choice TEXT NOT NULL,
  outcome TEXT NOT NULL,
  at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS attempts_profile_at ON attempts(profile_id, at);
CREATE INDEX IF NOT EXISTS attempts_asset ON attempts(asset_id);

CREATE TABLE IF NOT EXISTS flags (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL REFERENCES profiles(id),
  asset_id TEXT NOT NULL,
  release_id TEXT NOT NULL,
  session_id TEXT,
  reason TEXT NOT NULL,
  suggested_species TEXT,
  at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS flags_asset ON flags(asset_id);
CREATE INDEX IF NOT EXISTS flags_profile_at ON flags(profile_id, at);

-- Versioned catalogs live in private R2. Exactly one row is active.
CREATE TABLE IF NOT EXISTS releases (
  id TEXT PRIMARY KEY,
  object_key TEXT NOT NULL,
  compatibility_key TEXT NOT NULL,
  created_at TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 0 CHECK(active IN (0,1))
);
CREATE UNIQUE INDEX IF NOT EXISTS releases_one_active ON releases(active) WHERE active = 1;
CREATE INDEX IF NOT EXISTS releases_created ON releases(created_at);
