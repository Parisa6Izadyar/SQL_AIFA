import csv

import pymupdf
import pytest

from aifa_pipeline.database import connect, import_catalog

URL = "https://api.aifa.gov.it/aifa-bdf-eif-be/1.0.0/organizzazione/1/farmaci/1234/stampati?ts=RCP"


@pytest.fixture
def catalog_file(tmp_path):
    path = tmp_path / "catalog.csv"
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Codice  AIC", "Principio Attivo", "Denominazione e Confezione", "Titolare AIC", "URL_PDF", "4.1 Indicazioni terapeutiche"])
        writer.writerow(["1234567", "Example ingredient", "Example product", "Example holder", URL, "Previous text"])
    return path


@pytest.fixture
def database(tmp_path, catalog_file):
    with connect(tmp_path / "test.sqlite") as connection:
        import_catalog(connection, catalog_file)
        yield connection


@pytest.fixture
def pdf_bytes():
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 60), "1. DENOMINAZIONE DEL MEDICINALE\nEXAMPLE PRODUCT\nAIC 001234567\n"
                         "4.1 Indicazioni terapeutiche\nSynthetic indication text.\n"
                         "4.2 Posologia e modo di somministrazione\n1.5 mg is a synthetic numeric example.\n"
                         "4.3 Controindicazioni\nSynthetic contraindication text.\n"
                         "4.9 Sovradosaggio\nSynthetic overdose text.\n"
                         "5. PROPRIETA FARMACOLOGICHE\nNot part of section 4.9.\n"
                         "6.2 Incompatibilita\nSynthetic incompatibility text.\n"
                         "6.3 Periodo di validita\nNot part of section 6.2.", fontsize=10)
        return document.tobytes()
