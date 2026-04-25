import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "pointless.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id            INTEGER PRIMARY KEY,
    slug          TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    description   TEXT,
    source_kind   TEXT NOT NULL,
    source_query  TEXT NOT NULL,
    fetched_at    TEXT
);

CREATE TABLE IF NOT EXISTS answers (
    id              INTEGER PRIMARY KEY,
    category_id     INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    canonical_name  TEXT NOT NULL,
    aliases_json    TEXT,
    wikidata_qid    TEXT,
    wiki_article    TEXT,
    extra_json      TEXT,
    UNIQUE(category_id, canonical_name)
);

CREATE INDEX IF NOT EXISTS idx_answers_category ON answers(category_id);
CREATE INDEX IF NOT EXISTS idx_answers_qid      ON answers(wikidata_qid);

CREATE TABLE IF NOT EXISTS obscurity_signals (
    id           INTEGER PRIMARY KEY,
    answer_id    INTEGER NOT NULL REFERENCES answers(id) ON DELETE CASCADE,
    signal_type  TEXT NOT NULL,
    value_num    REAL,
    value_text   TEXT,
    source       TEXT,
    captured_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(answer_id, signal_type, source)
);

CREATE INDEX IF NOT EXISTS idx_signals_answer ON obscurity_signals(answer_id);
CREATE INDEX IF NOT EXISTS idx_signals_type   ON obscurity_signals(signal_type);

CREATE TABLE IF NOT EXISTS obscurity_scores (
    answer_id    INTEGER PRIMARY KEY REFERENCES answers(id) ON DELETE CASCADE,
    score        REAL NOT NULL,
    components_json TEXT,
    computed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(db_path: Path = DEFAULT_DB_PATH) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
