from collections import Counter
from pathlib import Path
import re

from .catalog import normalize_aic
from .sections import SECTIONS, normalize


def column_letter(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def plan_updates(connection, values):
    """Prepare cell changes without replacing missing or ambiguous document text."""
    if not values:
        raise ValueError("The worksheet is empty")
    headers = values[0]
    aic_columns = [i for i, header in enumerate(headers) if normalize(header) in {"codice aic", "aic"}]
    if len(aic_columns) != 1:
        raise ValueError("The worksheet must have exactly one AIC column")
    section_columns = {code: [i for i, h in enumerate(headers) if re.match(rf"^{re.escape(code)}\s", h)] for code in SECTIONS}
    if any(len(cols) > 1 for cols in section_columns.values()):
        raise ValueError("The worksheet has duplicate section columns")
    if not any(section_columns.values()):
        raise ValueError("No supported section column exists in the worksheet")
    indexed = []
    for number, row in enumerate(values[1:], start=2):
        raw = row[aic_columns[0]] if len(row) > aic_columns[0] else ""
        if str(raw).strip():
            indexed.append((number, normalize_aic(raw), row))
    counts = Counter(aic for _, aic, _ in indexed)
    if any(count > 1 for count in counts.values()):
        raise ValueError("The worksheet contains duplicate AIC identifiers; resolve them before exporting")
    updates, skipped = [], []
    for number, aic, row in indexed:
        matches = connection.execute(
            "SELECT DISTINCT d.latest_sha256 FROM products p "
            "JOIN catalog_rows c ON c.aic = p.aic JOIN documents d ON d.url = c.document_url "
            "JOIN document_product_checks k ON k.url = d.url AND k.sha256 = d.latest_sha256 AND k.aic = p.aic "
            "WHERE p.aic = ? AND p.review_required = 0 AND k.status = 'present' AND d.last_error IS NULL", (aic,)
        ).fetchall()
        if len(matches) != 1:
            skipped.append({"aic": aic, "reason": "No single current document with a matching AIC"})
            continue
        sections = connection.execute("SELECT code, text FROM extracted_sections WHERE sha256 = ?", (matches[0][0],)).fetchall()
        if any(n > 1 for n in Counter(s["code"] for s in sections).values()):
            skipped.append({"aic": aic, "reason": "Repeated sections require formulation review"})
            continue
        for section in sections:
            columns = section_columns[section["code"]]
            text = section["text"]
            if not columns or not text or len(text) > 49000:
                continue
            index = columns[0]
            existing = str(row[index]) if len(row) > index else ""
            if existing != text:
                updates.append({"range": f"{column_letter(index + 1)}{number}", "values": [[text]]})
    return {"updates": updates, "skipped": skipped, "cell_count": len(updates)}


def export_sheet(connection, spreadsheet_id, worksheet_name, credentials: Path, apply=False, client=None):
    if client is None:
        try:
            import gspread
        except ImportError as error:
            raise ValueError("Install requirements-sheets.txt for Google Sheets export") from error
        if not credentials.is_file():
            raise ValueError("Set GOOGLE_APPLICATION_CREDENTIALS to a local service account JSON file")
        client = gspread.service_account(filename=str(credentials), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    worksheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
    plan = plan_updates(connection, worksheet.get_all_values())
    plan["applied"] = False
    if apply:
        for offset in range(0, len(plan["updates"]), 100):
            worksheet.batch_update(data=plan["updates"][offset:offset + 100], value_input_option="RAW")
        plan["applied"] = True
    return plan
