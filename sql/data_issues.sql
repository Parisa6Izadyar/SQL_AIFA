SELECT c.source_row, c.aic, c.name, i.code, i.detail
FROM data_issues i
JOIN catalog_rows c ON c.id = i.row_id
ORDER BY c.source_row, i.code;
