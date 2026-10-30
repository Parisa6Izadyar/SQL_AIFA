SELECT ingredient, COUNT(*) AS unique_aic,
       SUM(review_required) AS requiring_review
FROM products
GROUP BY ingredient
ORDER BY unique_aic DESC, ingredient;
