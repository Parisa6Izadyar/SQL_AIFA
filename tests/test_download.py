from unittest.mock import MagicMock

import pytest
import requests

from aifa_pipeline.download import fetch_pdf
from aifa_pipeline.pipeline import process_documents, store_document
from conftest import URL


def response_session(data):
    session = MagicMock()
    response = session.get.return_value.__enter__.return_value
    response.status_code = 200
    response.iter_content.return_value = [data]
    return session


def test_cache_reuse_and_corruption(tmp_path, pdf_bytes):
    session = response_session(pdf_bytes)
    assert fetch_pdf(URL, tmp_path, session) == pdf_bytes
    assert fetch_pdf(URL, tmp_path, session) == pdf_bytes
    assert session.get.call_count == 1
    session.get.assert_called_once_with(URL, timeout=(5, 20), stream=True, allow_redirects=False)
    next(tmp_path.glob("*.pdf")).write_bytes(b"%PDF-corrupt")
    with pytest.raises(ValueError, match="checksum"):
        fetch_pdf(URL, tmp_path, session)


@pytest.mark.parametrize("body, limit", [(b"<html>not a PDF</html>", 100), (b"%PDF-too large", 5)])
def test_bad_response_is_not_cached(tmp_path, body, limit):
    with pytest.raises(ValueError):
        fetch_pdf(URL, tmp_path, response_session(body), max_bytes=limit)
    assert not list(tmp_path.glob("*.pdf"))


def test_failed_refresh_preserves_previous_sections(database, pdf_bytes, tmp_path):
    first = store_document(database, URL, pdf_bytes)
    count = database.execute("SELECT COUNT(*) FROM extracted_sections").fetchone()[0]
    session = MagicMock(); session.get.side_effect = requests.Timeout("test timeout")
    results = process_documents(database, tmp_path, limit=1, refresh=True, session=session, delay=0)
    assert results[0]["status"] == "error"
    assert database.execute("SELECT latest_sha256 FROM documents").fetchone()[0] == first["sha256"]
    assert database.execute("SELECT COUNT(*) FROM extracted_sections").fetchone()[0] == count
    assert database.execute("SELECT text FROM legacy_sections WHERE code='4.1'").fetchone()[0] == "Previous text"


def test_same_document_does_not_duplicate_sections(database, pdf_bytes):
    store_document(database, URL, pdf_bytes)
    first = database.execute("SELECT COUNT(*) FROM extracted_sections").fetchone()[0]
    store_document(database, URL, pdf_bytes)
    assert database.execute("SELECT COUNT(*) FROM extracted_sections").fetchone()[0] == first
    assert database.execute("SELECT status FROM document_product_checks").fetchone()[0] == "present"


def test_wrong_product_identity_is_exposed(database, pdf_bytes):
    database.execute("INSERT INTO products SELECT '009999999', name, ingredient, holder, atc, 0 FROM products")
    database.execute("UPDATE catalog_rows SET aic = '009999999'")
    database.commit()
    store_document(database, URL, pdf_bytes)
    assert database.execute("SELECT status FROM document_product_checks").fetchone()[0] == "not_found"
