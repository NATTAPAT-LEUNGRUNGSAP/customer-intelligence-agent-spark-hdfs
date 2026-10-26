-- Keep all source rows, including duplicates; report duplicate counts separately.
WITH typed AS (
 SELECT *,
   nullif(trim(invoice_id), '') AS invoice_clean,
   nullif(regexp_replace(trim(customer_id), '\\.0$', ''), '') AS customer_clean,
   try_cast(quantity AS BIGINT) AS quantity_num,
   try_cast(unit_price AS DECIMAL(18,4)) AS price_num,
   try_cast(invoice_ts AS TIMESTAMP) AS timestamp_value
 FROM raw_retail
)
SELECT invoice_clean AS invoice_id, customer_clean AS customer_id,
       nullif(trim(product_id), '') AS product_id, description,
       timestamp_value AS invoice_ts, nullif(trim(country), '') AS country,
       quantity_num AS quantity, price_num AS unit_price,
       cast(quantity_num * price_num AS DECIMAL(28,4)) AS line_amount,
       CASE
         WHEN invoice_clean IS NULL OR timestamp_value IS NULL
           OR nullif(trim(product_id), '') IS NULL
           OR quantity_num IS NULL OR price_num IS NULL THEN 'invalid'
         WHEN upper(invoice_clean) LIKE 'C%' THEN 'cancellation'
         WHEN quantity_num < 0 AND price_num > 0 THEN 'return'
         WHEN quantity_num > 0 AND price_num > 0 THEN 'sale'
         ELSE 'adjustment'
       END AS transaction_type,
       source_sheet, try_cast(source_row AS BIGINT) AS source_row
FROM typed
