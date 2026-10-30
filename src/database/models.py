SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url_hash      TEXT NOT NULL UNIQUE,
    category      TEXT NOT NULL,           -- CATEGORY_1_SCHOLARSHIP | CATEGORY_2_COOP_PARTTIME | CATEGORY_3_FULLTIME
    title         TEXT NOT NULL,
    organization  TEXT,
    location      TEXT,
    direct_url    TEXT NOT NULL,
    deadline      TEXT,
    funding       TEXT,
    moi_accepted  TEXT,                    -- yes | no | unknown
    gre_required  TEXT,
    match_score   INTEGER,
    why_it_matches TEXT,
    notes         TEXT,
    source        TEXT,                    -- where we found it (scraper name, 'research:gemini', ...)
    verification  TEXT DEFAULT 'unchecked',-- verified | blocked | dead | unchecked
    status        TEXT DEFAULT 'new',      -- new | sent | ignored | tailoring | applied | closed
    first_seen    TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen     TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_opp_category_status ON opportunities(category, status);

CREATE TABLE IF NOT EXISTS discovered_sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url_hash        TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,         -- portal | job_board | telegram | x_account | youtube | rss | api | other
    url             TEXT NOT NULL,
    region          TEXT,
    category        TEXT,
    access_method   TEXT,                  -- rss | api | static_html | js_required | login_required
    scraping_notes  TEXT,
    language        TEXT,
    quality         INTEGER,
    enabled         INTEGER DEFAULT 1,
    verification    TEXT DEFAULT 'unchecked',
    origin          TEXT DEFAULT 'seed',   -- seed | research | discovery
    yield_count     INTEGER DEFAULT 0,
    last_scraped    TEXT,
    added_at        TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(id),
    status         TEXT DEFAULT 'drafting', -- drafting | awaiting_approval | submitted | handed_off | failed
    submitted_at   TEXT,
    audit_log      TEXT,
    pc_kit_path    TEXT
);

CREATE TABLE IF NOT EXISTS tailored_docs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER NOT NULL REFERENCES opportunities(id),
    kind           TEXT NOT NULL,           -- cv | sop | cover_letter | cold_email
    path           TEXT NOT NULL,
    created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_dir    TEXT NOT NULL,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    summary    TEXT
);
"""
