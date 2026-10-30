from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aifa_pipeline.pipeline import store_document
from aifa_pipeline.sheets import export_sheet, plan_updates
from conftest import URL

VALUES = [["Codice AIC", "4.1 Indicazioni terapeutiche", "4.6 Fertilita, gravidanza e allattamento"],
          ["001234567", "Previous text", "Keep this existing text"]]


def test_missing_extraction_does_not_erase_cells(database):
    assert plan_updates(database, VALUES)["updates"] == []


def test_preview_never_writes_and_apply_uses_raw(database, pdf_bytes):
    store_document(database, URL, pdf_bytes)
    client = MagicMock()
    worksheet = client.open_by_key.return_value.worksheet.return_value
    worksheet.get_all_values.return_value = VALUES
    preview = export_sheet(database, "sheet-id", "Data", Path("not-needed.json"), client=client)
    assert preview["cell_count"] == 1
    assert preview["updates"][0]["range"] == "B2"
    worksheet.batch_update.assert_not_called()
    export_sheet(database, "sheet-id", "Data", Path("not-needed.json"), apply=True, client=client)
    assert worksheet.batch_update.call_args.kwargs["value_input_option"] == "RAW"


def test_repeated_sections_require_review(database, pdf_bytes):
    stored = store_document(database, URL, pdf_bytes)
    database.execute("INSERT INTO extracted_sections VALUES (?, '4.1', 2, 1, 1, 'Another formulation')", (stored["sha256"],))
    assert plan_updates(database, VALUES)["updates"] == []


def test_duplicate_sheet_keys_are_rejected(database):
    with pytest.raises(ValueError, match="duplicate AIC"):
        plan_updates(database, VALUES + [VALUES[1]])
