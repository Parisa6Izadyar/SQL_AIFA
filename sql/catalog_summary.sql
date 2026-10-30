SELECT
    (SELECT COUNT(*) FROM catalog_rows) AS source_rows,
    (SELECT COUNT(*) FROM products) AS unique_aic,
    (SELECT COUNT(DISTINCT ingredient) FROM products) AS active_ingredients,
    (SELECT COUNT(*) FROM documents) AS distinct_pdf_urls,
    (SELECT COUNT(*) FROM catalog_rows WHERE document_url IS NOT NULL) AS rows_with_pdf_url,
    (SELECT COUNT(*) FROM catalog_rows WHERE document_url IS NULL) AS rows_without_pdf_url,
    (SELECT COUNT(*) FROM products WHERE review_required = 1) AS products_requiring_review,
    (SELECT COUNT(*) FROM documents WHERE latest_sha256 IS NOT NULL) AS extracted_documents;
