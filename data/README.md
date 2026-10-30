# Project input files

The original data files are retained as supplied. They are historical project artifacts and may contain incomplete or inconsistent values.

| File | Role |
| --- | --- |
| `sql_link_pdf - parisa - Sheet1.csv` | Default 332-row sample, with package metadata, PDF URLs and historical extracted section text |
| `AIFA_Dataset_V1.xlsx` | Alternative 332-row workbook with the same AIC sequence and Italian section-column titles |
| `BETA PHARMACY.xlsx` | Earlier, broader working catalog; most section and URL fields are empty |
| `merged_excel_A_H.xlsx` | Earlier merged working file with incomplete/misaligned fields; not used in the verified workflow |

The recorded results use only the default CSV. The two 332-row files contain the same identifiers but differ in historical text formatting and column names; they are not merged. A different input file needs a separate `--output` directory.

PDFs are downloaded from URLs already present in the sample. The local build does not query the live registry to refresh package status, prices or authorization holders. See [quality notes](../docs/data_quality.md) for known source issues and [AIFA medicine search](https://medicinali.aifa.gov.it/) for the current source service.
