from datetime import datetime, timezone
import hashlib
from pathlib import Path
import time

import requests
import pymupdf

from . import __version__
from .download import fetch_pdf, make_session
from .extract import parse_pdf


def store_document(connection, url, data):
    parsed = parse_pdf(data)
    if not any(section.text for section in parsed.sections):
        raise ValueError("No supported RCP section with extractable text was found")
    checksum = hashlib.sha256(data).hexdigest()
    with connection:
        connection.execute("INSERT INTO pdf_versions VALUES (?, ?, ?) "
                           "ON CONFLICT(sha256) DO UPDATE SET page_count = excluded.page_count, parser_version = excluded.parser_version",
                           (checksum, parsed.page_count, __version__))
        connection.execute("DELETE FROM extracted_sections WHERE sha256 = ?", (checksum,))
        connection.executemany("INSERT INTO extracted_sections VALUES (?, ?, ?, ?, ?, ?)",
                               [(checksum, s.code, s.occurrence, s.page_start, s.page_end, s.text) for s in parsed.sections])
        products = connection.execute("SELECT DISTINCT aic FROM catalog_rows WHERE document_url = ?", (url,)).fetchall()
        connection.executemany("INSERT OR REPLACE INTO document_product_checks VALUES (?, ?, ?, ?)",
                               [(url, checksum, row["aic"], "present" if row["aic"] in parsed.aics else "not_found") for row in products])
        connection.execute("UPDATE documents SET latest_sha256 = ?, last_error = NULL WHERE url = ?", (checksum, url))
        connection.execute("INSERT INTO document_fetches(url, fetched_at, sha256) VALUES (?, ?, ?)",
                           (url, datetime.now(timezone.utc).isoformat(), checksum))
    return {"url": url, "sha256": checksum, "pages": parsed.page_count, "section_occurrences": len(parsed.sections),
            "distinct_sections": len({s.code for s in parsed.sections})}


def process_documents(connection, cache: Path, limit=3, refresh=False, session=None, delay=1.0):
    if limit < 1:
        raise ValueError("--limit must be at least 1")
    if delay < 0:
        raise ValueError("--delay cannot be negative")
    urls = connection.execute(
        "SELECT DISTINCT c.document_url FROM catalog_rows c JOIN products p ON p.aic = c.aic "
        "WHERE c.document_url IS NOT NULL AND p.review_required = 0 ORDER BY c.id"
    ).fetchall()[:limit]
    own_session = session is None
    session = session or make_session()
    results = []
    try:
        for index, row in enumerate(urls):
            url = row["document_url"]
            try:
                data = fetch_pdf(url, cache, session, refresh=refresh)
                result = store_document(connection, url, data)
                result["status"] = "ok"
            except (requests.RequestException, ValueError, OSError, pymupdf.FileDataError, RuntimeError) as error:
                message = f"{type(error).__name__}: {error}"
                with connection:
                    connection.execute("UPDATE documents SET last_error = ? WHERE url = ?", (message, url))
                    connection.execute("INSERT INTO document_fetches(url, fetched_at, error) VALUES (?, ?, ?)",
                                       (url, datetime.now(timezone.utc).isoformat(), message))
                result = {"url": url, "status": "error", "error": message}
            results.append(result)
            print(f"Document {index + 1}/{len(urls)}: {result['status']}", flush=True)
            if index + 1 < len(urls):
                time.sleep(delay)
    finally:
        if own_session:
            session.close()
    return results
