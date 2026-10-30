# Snapshot quality notes

These observations refer to the checked-in 332-row CSV, SHA-256 `b8aaa79716707a960b0bc7bc147a6a6a9d1cb444fb82f902428f0edef82ebaaa`. They do not describe the complete AIFA registry.

| Observation | Handling |
| --- | --- |
| All 332 raw AIC values are shorter than nine digits | Restore leading zeros in the database; retain raw identifiers |
| AIC `040400234` appears at CSV rows 151 and 157 with different authorization holders | Keep both rows; flag the package; do not select one holder automatically |
| CSV row 2 names ARTANE, AIC `003488057`, but its URL points to product number 34885 | Flag the link/AIC-prefix discrepancy and exclude it from automatic extraction |
| Eleven URL cells contain `NON` and one is empty | Report 12 source rows without a usable URL |
| Nine section 4.5 cells end in `[TRUNCATED]` | Preserve the text and mark it truncated |
| Section 4.6 has 92 missing/marker cells; each other target section has 59 | Report availability separately from verified extraction |

On 30 October 2026 the row-2 URL returned a four-page PDF headed Nadixa, listing AICs `034885020`, `034885032`, `034885044` and `034885057`; none matches `003488057`. The downloaded PDF SHA-256 was `e9c3acd6ed8a9ba2e4fa4b0ca13f184844b3cb4af91a200015b0a618106783d8`. The project does not guess a replacement URL.

Live requests also exposed a historical link returning HTTP 404, for URL product number 48222. Valid URL syntax does not establish availability. Download failures are recorded in the local database and `extraction_run.json`; they do not become `Not found` content or erase earlier text.

Several packages share the same PDF. A document can contain multiple RCPs for different formulations; the two-document verified run contains five and two occurrences per target section respectively. Such text cannot be treated as a package-specific instruction merely because a package AIC appears somewhere in the PDF.
