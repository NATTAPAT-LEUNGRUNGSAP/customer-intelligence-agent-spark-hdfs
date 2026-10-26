-- Exclude entire invoices with inconsistent customer/country, including missing/nonmissing mixes.
WITH eligible AS (
 SELECT * FROM sales_lines WHERE transaction_type = 'sale'
), consistent AS (
 SELECT invoice_id FROM eligible GROUP BY invoice_id
 HAVING count(DISTINCT struct(customer_id)) = 1
    AND count(DISTINCT struct(country)) = 1
)
SELECT s.invoice_id, first(s.customer_id) AS customer_id,
       min(s.invoice_ts) AS order_ts, first(s.country) AS country,
       sum(s.line_amount) AS order_amount, sum(s.quantity) AS total_units,
       count(DISTINCT s.product_id) AS distinct_products
FROM eligible s JOIN consistent c ON s.invoice_id = c.invoice_id
GROUP BY s.invoice_id
