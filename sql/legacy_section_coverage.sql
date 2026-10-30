SELECT s.code, s.title, COUNT(*) AS source_rows,
       SUM(l.status = 'missing') AS missing,
       SUM(l.status = 'unverified') AS unverified,
       SUM(l.status = 'truncated') AS truncated
FROM section_types s
JOIN legacy_sections l ON l.code = s.code
GROUP BY s.code, s.title
ORDER BY s.code;
