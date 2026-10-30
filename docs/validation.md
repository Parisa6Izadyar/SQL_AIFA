# Validation record

## Local execution

The workflow was tested on 30 October 2026 with Python 3.12.14 and the packages in `requirements.txt`.

```bash
python -m pytest -q
python -m aifa_pipeline build
python -m aifa_pipeline extract --limit 2 --refresh
```

All 36 tests passed. The bundled CSV built a database with 332 source rows, 331 distinct package AICs, 58 distinct ingredient labels and 148 valid-format PDF URLs. Repeating the build did not duplicate rows. All six SQL reports were produced, and SQLite integrity and foreign-key checks passed.

The live extraction command successfully downloaded two PDFs covering 76 pages, retained 70 nonempty target-section occurrences and found all ten target types in each PDF. Four linked package AICs were found literally in the PDF text. The content hashes and per-document coverage are recorded under `results/benchmark/`.

These are operational checks on two PDFs, not an annotated extraction-accuracy evaluation. Page layouts and headings were inspected, including the 4.9-to-5 and 6.2-to-6.3 boundaries. No claim is made that every extracted table or medical statement is complete or correct.

## Regression tests

The suite checks identifier normalization and invalid values, ambiguous input columns, CSV/XLSX agreement, conflicting source metadata, idempotent import, foreign keys, disjoint historical/fresh text, heading boundaries, wrapped titles, pregnancy-title variants, repeated sections, numeric body text, PDF parsing and literal AIC checks. Download tests cover cache reuse, checksums, malformed cache metadata, response type/size and failure preservation. Reprocessing a PDF replaces the previous parser output within a transaction. A fake Sheets client checks preview behavior, RAW writes, missing/repeated sections and duplicate worksheet identifiers.

## Continuous integration and hosted execution

GitHub Actions installs the pinned dependencies, runs the test suite, builds the actual bundled catalog and regenerates its SQL reports. It does not require secrets, live AIFA availability or a Google account. Synthetic PDF fixtures exercise extraction; they are not real clinical documents.

On 30 October 2026 the repository owner ran `python -m aifa_pipeline extract --limit 2` in GitHub Codespaces and shared its completed output: `extracted_documents: 2` and `Finished. Results: ...`. This confirms the hosted extraction command. The test-suite counts above come from local execution and CI.

Google Sheets export has been tested with a fake client, not a private spreadsheet or a live write.
