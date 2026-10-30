from collections import Counter
from dataclasses import dataclass
import re

import pymupdf

from .sections import TITLE_PREFIXES, normalize

STOP_TITLES = {
    "1": ("denominazione", "name of the medicinal"),
    "2": ("composizione", "qualitative and quantitative"),
    "3": ("forma farmaceutica", "pharmaceutical form"),
    "4": ("informazioni cliniche", "clinical particulars"),
    "5": ("proprieta farmacologiche", "pharmacological properties"),
    "5.1": ("proprieta farmacodinamiche", "pharmacodynamic"),
    "5.2": ("proprieta farmacocinetiche", "pharmacokinetic"),
    "5.3": ("dati preclinici", "preclinical"),
    "6": ("informazioni farmaceutiche", "pharmaceutical particulars"),
    "6.1": ("elenco degli eccipienti", "list of excipients"),
    "6.3": ("periodo di validita", "shelf life"),
    "6.4": ("precauzioni particolari", "special precautions"),
    "6.5": ("natura", "nature and contents"),
    "6.6": ("precauzioni", "special precautions"),
    "7": ("titolare", "marketing authorisation holder"),
    "8": ("numero", "numeri", "marketing authorisation number"),
    "9": ("data", "date of first authorisation"),
    "10": ("data", "date of revision"),
}
HEADER = re.compile(r"^(\d{1,2}(?:\.\d{1,2})?)(?!\d)(?!\.\d)\s*[.\-–:]?\s*(.*)$")


@dataclass(frozen=True)
class Line:
    page: int
    text: str


@dataclass(frozen=True)
class Section:
    code: str
    occurrence: int
    page_start: int
    page_end: int
    text: str


@dataclass
class ParsedDocument:
    page_count: int
    sections: list[Section]
    aics: set[str]


def pdf_lines(data: bytes) -> tuple[int, list[Line]]:
    if not data.startswith(b"%PDF-"):
        raise ValueError("The response is not a PDF")
    lines = []
    with pymupdf.open(stream=data, filetype="pdf") as document:
        if document.needs_pass or not len(document):
            raise ValueError("The PDF is empty or password protected")
        for page in document:
            for block in page.get_text("dict", sort=True)["blocks"]:
                if block["type"] != 0:
                    continue
                block_text = " ".join(s["text"] for line in block["lines"] for s in line["spans"])
                if block_text.strip().startswith(("Esula dalla competenza", "Documento reso disponibile da AIFA")):
                    continue
                for line in block["lines"]:
                    if abs(line["dir"][1]) > 0.1:
                        continue
                    text = re.sub(r"\s+", " ", "".join(s["text"] for s in line["spans"])).strip()
                    if not text or text == "Agenzia Italiana del Farmaco":
                        continue
                    if re.fullmatch(r"(?:Pagina\s+)?\d+(?:\s*(?:di|/)\s*\d+)?", text, re.I):
                        if line["bbox"][1] > page.rect.height * 0.90 or line["bbox"][3] < page.rect.height * 0.08:
                            continue
                    lines.append(Line(page.number + 1, text))
        return len(document), lines


def find_header(lines: list[Line], index: int):
    match = HEADER.match(lines[index].text)
    if not match:
        return None
    code, title = match.groups()
    prefixes = TITLE_PREFIXES.get(code, STOP_TITLES.get(code))
    if not prefixes:
        return None
    candidate = title
    for consumed in range(1, 4):
        if any(normalize(candidate).startswith(prefix) for prefix in prefixes):
            return code, consumed
        if index + consumed >= len(lines) or lines[index + consumed].page != lines[index].page:
            break
        candidate += " " + lines[index + consumed].text
    return None


def extract_sections(lines: list[Line]) -> list[Section]:
    sections = []
    counts = Counter()
    current = None
    content = []
    first_page = last_page = 1

    def finish():
        if current is not None:
            counts[current] += 1
            sections.append(Section(current, counts[current], first_page, last_page, " ".join(content).strip()))

    index = 0
    while index < len(lines):
        line = lines[index]
        header = find_header(lines, index)
        if header:
            finish()
            code, consumed = header
            current = code if code in TITLE_PREFIXES else None
            content = []
            first_page = last_page = line.page
            index += consumed
            continue
        if current is not None:
            content.append(line.text)
            last_page = line.page
        index += 1
    finish()
    return sections


def parse_pdf(data: bytes) -> ParsedDocument:
    pages, lines = pdf_lines(data)
    text = " ".join(line.text for line in lines)
    aics = set(re.findall(r"(?<!\d)0\d{8}(?!\d)", text))
    return ParsedDocument(pages, extract_sections(lines), aics)
