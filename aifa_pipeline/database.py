from collections import defaultdict
from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3

from .catalog import load_catalog
from .sections import SECTIONS, missing_text

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.executescript((ROOT / "sql/schema.sql").read_text())
        with connection:
            connection.executemany("INSERT OR IGNORE INTO section_types VALUES (?, ?)", SECTIONS.items())
        yield connection
    finally:
        connection.close()


def import_catalog(connection, path: Path):
    rows = load_catalog(path)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    existing = connection.execute("SELECT id FROM sources WHERE sha256 = ?", (checksum,)).fetchone()
    if existing:
        return existing["id"]
    if connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]:
        raise ValueError("This database already contains another catalog; use a separate output directory")
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.aic].append(row)
    with connection:
        source_id = connection.execute("INSERT INTO sources(sha256, filename, row_count) VALUES (?, ?, ?)",
                                       (checksum, path.name, len(rows))).lastrowid
        for aic, group in grouped.items():
            fields = {}
            conflicts = []
            for field in ("name", "ingredient", "holder", "atc", "url"):
                values = {getattr(r, field) for r in group if getattr(r, field)}
                fields[field] = next(iter(values)) if len(values) == 1 else None
                if len(values) > 1:
                    conflicts.append(field)
            review = bool(conflicts or any(code == "url_aic_prefix_mismatch" for r in group for code, _ in r.issues))
            connection.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)",
                               (aic, fields["name"], fields["ingredient"],
                                fields["holder"], fields["atc"], int(review)))
            for row in group:
                if row.url:
                    connection.execute("INSERT OR IGNORE INTO documents(url) VALUES (?)", (row.url,))
                row_id = connection.execute(
                    "INSERT INTO catalog_rows(source_id, source_row, aic, raw_aic, name, ingredient, holder, atc, document_url) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (source_id, row.source_row, aic, row.raw_aic, row.name, row.ingredient, row.holder, row.atc, row.url),
                ).lastrowid
                issues = list(row.issues)
                if len(group) > 1:
                    issues.append(("duplicate_aic", f"{len(group)} source rows"))
                if conflicts:
                    issues.append(("conflicting_aic_metadata", ", ".join(conflicts)))
                connection.executemany("INSERT INTO data_issues VALUES (?, ?, ?)",
                                       [(row_id, code, detail) for code, detail in issues])
                for code, text in row.sections.items():
                    status = "missing" if missing_text(text) else "truncated" if "[TRUNCATED]" in text else "unverified"
                    connection.execute("INSERT INTO legacy_sections VALUES (?, ?, ?, ?)", (row_id, code, text, status))
    return source_id
