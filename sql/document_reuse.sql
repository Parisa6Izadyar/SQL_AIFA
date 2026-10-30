SELECT c.document_url, COUNT(*) AS source_rows, COUNT(DISTINCT c.aic) AS unique_aic
FROM catalog_rows c
WHERE c.document_url IS NOT NULL
GROUP BY c.document_url
ORDER BY unique_aic DESC, c.document_url;
