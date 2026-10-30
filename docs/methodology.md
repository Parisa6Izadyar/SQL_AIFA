# Data preparation and extraction

## Catalog import

The default input is `data/sql_link_pdf - parisa - Sheet1.csv`. CSV and XLSX readers load identifiers as text. Whitespace in column names is normalized; section columns are identified by their numeric code, so the Italian XLSX and mixed-language CSV map to the same ten section types.

AIC values must contain one to nine ASCII digits. Short values are padded on the left to nine digits, with the original value retained in `catalog_rows.raw_aic`. This restores the source format; it is not a check against the current authorization register or an AIC check-digit validator.

Each source file has a SHA-256 identifier. Importing the same file again is idempotent. A different catalog requires a separate output directory, preventing accidental mixing of snapshots. Products are keyed by AIC; source rows remain separate. Conflicting nonempty metadata sets `products.review_required` and leaves the conflicting canonical field null. Both source values and their row numbers remain available.

The URL validator accepts the AIFA RCP route used in the snapshot. Missing markers such as `NON` become missing links. A discrepancy between the URL's product-number segment and the first six AIC digits is a review heuristic. It does not prove document identity. The current sample contains one such discrepancy, confirmed by inspecting the returned PDF.

## Historical text

`legacy_sections` stores all ten cells per source row without truncating or silently replacing them. Empty cells and `Not found` / `NON - TROVATO` markers are classified as missing. Existing `[TRUNCATED]` suffixes are classified separately. Other values are unverified: a populated cell is not evidence that its text is correct, complete or matched to the package.

The original workbooks and CSV are unchanged. Importing another workbook does not merge it into the default sample.

## Download and provenance

Extraction selects distinct document URLs linked to products without metadata/link-review flags, in source-row order. It never requests the same URL once per package. The default limit is three; the documented small live run uses `--limit 2`.

Requests use HTTPS, a 5-second connection timeout, a 20-second read timeout, two bounded retries for transient statuses and a 30 MiB response limit. Redirects are rejected. Downloads are sequential, with a one-second interval by default. The cache key is the URL hash and its manifest contains the PDF's SHA-256. Corrupted cached files are rejected; `--refresh` explicitly replaces the cached response.

Each successfully parsed PDF has a content hash, page count and parser version. Fetch attempts record their time and either the hash or error. A failed attempt preserves the last successful PDF association and extracted text. Failed documents are excluded from Sheets export until a successful processing attempt clears the error.

## Section parsing

PyMuPDF provides text lines and page coordinates. The parser ignores rotated watermark lines, recognized AIFA footer blocks and marginal page numbers. It accepts supported Italian/English title prefixes, a section number on a separate line, optional punctuation and selected title variants.

The target types are 4.1 through 4.9 and 6.2. Recognized non-target headings also end capture. For example, section 5 ends 4.9, and 6.3 ends 6.2. A numeric dose such as `1.5 mg` remains body text. Each repeated heading creates a separate occurrence with a page range; text from different formulations is not combined into a single value.

Literal nine-digit AIC strings in the PDF are compared with linked catalog packages. A missing identifier is recorded as `not_found`, not inferred from a similar name. Even a present identifier does not establish which formulation a particular paragraph describes.

This is a rule-based text parser. It does not reconstruct tables, perform OCR or identify every possible heading layout. Counts of detected sections measure coverage, not precision, recall or medical correctness.

## Google Sheets

The exporter is optional and preview-only by default. Authentication uses an explicit local service-account file and the Sheets scope. The spreadsheet is opened by ID, avoiding title collisions. Nothing in the local build authenticates or reads a private sheet.

The worksheet must have exactly one AIC column. Duplicate normalized AICs or ambiguous section columns stop export. Each eligible package needs one current parsed document, a literal matching AIC, no catalog review flag and no last processing error. Any repeated target heading in that PDF causes the document to be skipped because its formulation cannot be selected safely.

Only nonempty, single-occurrence sections under 49,001 characters are proposed. Missing or long text is skipped rather than replaced by a marker or cut off. The preview lists changed cells and skipped package reasons. `--apply` writes those cells with RAW input mode, up to 100 cells per request, preserving unrelated fields. Multiple API batches are not a transaction; an API failure after a successful batch can leave a partial update. Rerun preview against the current sheet before retrying.
