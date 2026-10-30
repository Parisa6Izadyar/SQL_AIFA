import csv
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3

from . import __version__
from .database import ROOT

REPORTS = ("catalog_summary", "legacy_section_coverage", "document_reuse", "data_issues", "extraction_coverage", "ingredient_counts")


def write_reports(connection, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    tables = {}
    for name in REPORTS:
        cursor = connection.execute((ROOT / "sql" / f"{name}.sql").read_text())
        rows = [dict(row) for row in cursor.fetchall()]
        tables[name] = rows
        with (output / f"{name}.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow([column[0] for column in cursor.description])
            writer.writerows([row.values() for row in rows])
    counts = {row["code"]: row["n"] for row in connection.execute("SELECT code, COUNT(*) n FROM data_issues GROUP BY code")}
    manifest = {
        "pipeline_version": __version__,
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "packages": {p: importlib.metadata.version(p) for p in ("pandas", "PyMuPDF", "requests", "openpyxl")},
        "sources": [dict(row) for row in connection.execute("SELECT filename, sha256, row_count FROM sources")],
        "catalog": tables["catalog_summary"][0],
        "issue_counts_by_source_row": counts,
        "legacy_sections": tables["legacy_section_coverage"],
        "document_versions": [dict(row) for row in connection.execute("SELECT * FROM pdf_versions ORDER BY sha256")],
        "identity_checks": [dict(row) for row in connection.execute("SELECT status, COUNT(*) n FROM document_product_checks GROUP BY status")],
        "interpretation": "Legacy text is unverified. Extracted section counts measure coverage, not clinical or extraction accuracy.",
    }
    (output / "metrics.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest
