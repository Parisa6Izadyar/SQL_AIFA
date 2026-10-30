import csv
import sqlite3

import pytest

from aifa_pipeline.catalog import load_catalog, normalize_aic, validate_url
from aifa_pipeline.database import ROOT, import_catalog


@pytest.mark.parametrize("raw, expected", [("3488057", "003488057"), ("24022129", "024022129"), ("024022129", "024022129")])
def test_aic_keeps_nine_digit_text(raw, expected):
    assert normalize_aic(raw) == expected


@pytest.mark.parametrize("raw", ["", "123.0", "1e7", "1234567890", "123456x"])
def test_invalid_aic_is_rejected(raw):
    with pytest.raises(ValueError):
        normalize_aic(raw)


def test_catalog_preserves_source_and_missing_marker(catalog_file):
    rows = load_catalog(catalog_file)
    assert rows[0].source_row == 2
    assert rows[0].aic == "001234567"
    assert rows[0].raw_aic == "1234567"
    assert rows[0].sections["4.1"] == "Previous text"
    assert validate_url("NON") is None


def test_conflicting_aic_keeps_both_rows(database, catalog_file):
    second = catalog_file.parent / "conflicting.csv"
    rows = list(csv.reader(catalog_file.open()))
    rows.append(list(rows[1])); rows[2][3] = "Another holder"
    with second.open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    database.execute("DELETE FROM legacy_sections")
    database.execute("DELETE FROM data_issues")
    database.execute("DELETE FROM catalog_rows")
    database.execute("DELETE FROM products")
    database.execute("DELETE FROM sources")
    database.commit()
    import_catalog(database, second)
    product = database.execute("SELECT * FROM products").fetchone()
    assert product["review_required"] == 1
    assert product["holder"] is None
    assert database.execute("SELECT COUNT(*) FROM catalog_rows").fetchone()[0] == 2
    assert database.execute("SELECT COUNT(*) FROM data_issues WHERE code = 'conflicting_aic_metadata'").fetchone()[0] == 2


def test_import_is_idempotent_and_foreign_keys_work(database, catalog_file):
    source = import_catalog(database, catalog_file)
    assert import_catalog(database, catalog_file) == source
    assert database.execute("SELECT COUNT(*) FROM catalog_rows").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        database.execute("INSERT INTO legacy_sections VALUES (999, '4.1', 'text', 'unverified')")


def test_another_catalog_does_not_overwrite_existing(database, catalog_file):
    changed = catalog_file.parent / "changed.csv"
    changed.write_text(catalog_file.read_text() + "\n")
    with pytest.raises(ValueError, match="another catalog"):
        import_catalog(database, changed)
    assert database.execute("SELECT COUNT(*) FROM catalog_rows").fetchone()[0] == 1


def test_arbitrary_url_is_rejected():
    for url in ("https://example.com/a.pdf", "http://api.aifa.gov.it/a.pdf", "https://api.aifa.gov.it/other"):
        with pytest.raises(ValueError):
            validate_url(url)


def test_existing_excel_and_csv_preserve_the_same_aics():
    excel = load_catalog(ROOT / "data/AIFA_Dataset_V1.xlsx")
    csv_rows = load_catalog(ROOT / "data/sql_link_pdf - parisa - Sheet1.csv")
    assert len(excel) == len(csv_rows) == 332
    assert [row.aic for row in excel] == [row.aic for row in csv_rows]
    assert excel[0].sections["4.3"]


def test_multiple_identifier_aliases_are_rejected(catalog_file):
    rows = list(csv.reader(catalog_file.open()))
    rows[0].append("AIC")
    rows[1].append("009999999")
    with catalog_file.open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    with pytest.raises(ValueError, match="Ambiguous input columns"):
        load_catalog(catalog_file)
