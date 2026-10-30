from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs

import pandas as pd

from .sections import SECTIONS, missing_text, normalize


@dataclass
class CatalogRow:
    source_row: int
    raw_aic: str
    aic: str
    ingredient: str
    name: str
    holder: str
    atc: str
    url: str | None
    sections: dict[str, str]
    issues: list[tuple[str, str]]


def normalize_aic(value: str) -> str:
    value = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,9}", value):
        raise ValueError(f"Invalid AIC identifier: {value!r}")
    return value.zfill(9)


def validate_url(value: str) -> str | None:
    if missing_text(value):
        return None
    parsed = urlparse(value.strip())
    if (parsed.scheme != "https" or parsed.hostname != "api.aifa.gov.it"
            or parsed.port not in (None, 443) or parsed.username or parsed.password
            or not re.fullmatch(r"/aifa-bdf-eif-be/1\.0\.0/organizzazione/\d+/farmaci/\d+/stampati", parsed.path)
            or parse_qs(parsed.query) != {"ts": ["RCP"]}):
        raise ValueError("Expected an HTTPS AIFA RCP document URL")
    return value.strip()


def load_catalog(path: Path) -> list[CatalogRow]:
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    elif path.suffix.lower() == ".xlsx":
        frame = pd.read_excel(path, dtype=str, keep_default_na=False)
    else:
        raise ValueError("Input must be a CSV or XLSX file")
    def column(*names, required=False):
        aliases = {normalize(name) for name in names}
        matches = [name for name in frame.columns if normalize(name) in aliases]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous input columns for {names[0]}: {matches}")
        if matches:
            return matches[0]
        if required:
            raise ValueError(f"Missing input column: {names[0]}")
        return None

    fields = {
        "raw_aic": column("Codice AIC", "AIC", required=True),
        "ingredient": column("Principio Attivo", required=True),
        "name": column("Denominazione e Confezione", required=True),
        "holder": column("Titolare AIC"),
        "atc": column("ATC"),
        "raw_url": column("URL_PDF", "URL"),
    }
    section_columns = {code: [c for c in frame.columns if re.match(rf"^{re.escape(code)}\s", c)] for code in SECTIONS}
    if any(len(cols) > 1 for cols in section_columns.values()):
        raise ValueError("More than one input column maps to the same section")
    rows = []
    for index, source in frame.iterrows():
        values = {key: str(source[col]).strip() if col else "" for key, col in fields.items()}
        aic = normalize_aic(values.pop("raw_aic"))
        raw_aic = str(source[fields["raw_aic"]]).strip()
        raw_url = values.pop("raw_url")
        issues = []
        if raw_aic != aic:
            issues.append(("aic_zero_padding", f"{raw_aic} -> {aic}"))
        try:
            url = validate_url(raw_url)
        except ValueError:
            url = None
            issues.append(("invalid_url", raw_url))
        if not url:
            issues.append(("missing_pdf_url", raw_url))
        else:
            product_number = re.search(r"/farmaci/(\d+)/", url)[1]
            if int(product_number) != int(aic[:6]):
                issues.append(("url_aic_prefix_mismatch", f"URL product {product_number}; AIC prefix {aic[:6]}"))
        sections = {code: str(source[cols[0]]).strip() if cols else "" for code, cols in section_columns.items()}
        rows.append(CatalogRow(index + 2, raw_aic, aic, **values, url=url, sections=sections, issues=issues))
    if not rows:
        raise ValueError("The input catalog is empty")
    return rows
