SELECT d.url, d.latest_sha256 AS sha256, s.code,
       COUNT(e.occurrence) AS occurrences,
       SUM(CASE WHEN length(e.text) > 0 THEN 1 ELSE 0 END) AS nonempty_occurrences,
       COALESCE(SUM(length(e.text)), 0) AS characters
FROM documents d
CROSS JOIN section_types s
LEFT JOIN extracted_sections e ON e.sha256 = d.latest_sha256 AND e.code = s.code
WHERE d.latest_sha256 IS NOT NULL
GROUP BY d.url, d.latest_sha256, s.code
ORDER BY d.url, s.code;
