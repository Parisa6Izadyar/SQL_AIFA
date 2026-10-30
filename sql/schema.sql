PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    row_count INTEGER NOT NULL CHECK (row_count > 0)
);

CREATE TABLE IF NOT EXISTS products (
    aic TEXT PRIMARY KEY CHECK (length(aic) = 9 AND aic NOT GLOB '*[^0-9]*'),
    name TEXT,
    ingredient TEXT,
    holder TEXT,
    atc TEXT,
    review_required INTEGER NOT NULL CHECK (review_required IN (0, 1))
);

CREATE TABLE IF NOT EXISTS documents (
    url TEXT PRIMARY KEY,
    latest_sha256 TEXT REFERENCES pdf_versions(sha256),
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS catalog_rows (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    source_row INTEGER NOT NULL,
    aic TEXT NOT NULL REFERENCES products(aic),
    raw_aic TEXT NOT NULL,
    name TEXT NOT NULL,
    ingredient TEXT NOT NULL,
    holder TEXT NOT NULL,
    atc TEXT NOT NULL,
    document_url TEXT REFERENCES documents(url),
    UNIQUE (source_id, source_row)
);
CREATE INDEX IF NOT EXISTS catalog_aic ON catalog_rows(aic);
CREATE INDEX IF NOT EXISTS catalog_document ON catalog_rows(document_url);

CREATE TABLE IF NOT EXISTS section_types (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS legacy_sections (
    row_id INTEGER NOT NULL REFERENCES catalog_rows(id),
    code TEXT NOT NULL REFERENCES section_types(code),
    text TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('missing', 'unverified', 'truncated')),
    PRIMARY KEY (row_id, code)
);

CREATE TABLE IF NOT EXISTS data_issues (
    row_id INTEGER NOT NULL REFERENCES catalog_rows(id),
    code TEXT NOT NULL,
    detail TEXT NOT NULL,
    PRIMARY KEY (row_id, code)
);

CREATE TABLE IF NOT EXISTS pdf_versions (
    sha256 TEXT PRIMARY KEY,
    page_count INTEGER NOT NULL CHECK (page_count > 0),
    parser_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS document_fetches (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL REFERENCES documents(url),
    fetched_at TEXT NOT NULL,
    sha256 TEXT REFERENCES pdf_versions(sha256),
    error TEXT
);

CREATE TABLE IF NOT EXISTS extracted_sections (
    sha256 TEXT NOT NULL REFERENCES pdf_versions(sha256),
    code TEXT NOT NULL REFERENCES section_types(code),
    occurrence INTEGER NOT NULL CHECK (occurrence > 0),
    page_start INTEGER NOT NULL CHECK (page_start > 0),
    page_end INTEGER NOT NULL CHECK (page_end >= page_start),
    text TEXT NOT NULL,
    PRIMARY KEY (sha256, code, occurrence)
);

CREATE TABLE IF NOT EXISTS document_product_checks (
    url TEXT NOT NULL REFERENCES documents(url),
    sha256 TEXT NOT NULL REFERENCES pdf_versions(sha256),
    aic TEXT NOT NULL REFERENCES products(aic),
    status TEXT NOT NULL CHECK (status IN ('present', 'not_found')),
    PRIMARY KEY (url, sha256, aic)
);
