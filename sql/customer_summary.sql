WITH historical AS (
 SELECT * FROM orders
 WHERE customer_id IS NOT NULL AND order_ts < TIMESTAMP '${AS_OF} 00:00:00'
), recent AS (
 SELECT customer_id, count(*) AS orders_180d, sum(order_amount) AS sales_180d,
        sum(order_amount) / count(*) AS aov_180d
 FROM historical
 WHERE order_ts >= TIMESTAMP '${AS_OF} 00:00:00' - INTERVAL 180 DAYS
 GROUP BY customer_id
), lifetime AS (
 SELECT customer_id, min(to_date(order_ts)) AS first_purchase_date,
        max(to_date(order_ts)) AS last_purchase_date
 FROM historical GROUP BY customer_id
), combined AS (
 SELECT l.*, DATE '${AS_OF}' AS as_of_date,
        datediff(DATE '${AS_OF}', l.last_purchase_date) AS recency_days,
        r.orders_180d, r.sales_180d, r.aov_180d
 FROM lifetime l JOIN recent r ON l.customer_id = r.customer_id
), ranked AS (
 SELECT *, row_number() OVER (ORDER BY sales_180d DESC, customer_id ASC) AS monetary_rank,
           count(*) OVER () AS population_size
 FROM combined
)
SELECT *, monetary_rank <= ceil(population_size * 0.2) AS is_high_value,
 CASE WHEN recency_days <= 30 AND orders_180d >= 3 THEN 'Champions'
      WHEN recency_days <= 30 AND orders_180d = 2 THEN 'Recent repeat'
      WHEN recency_days <= 30 THEN 'Recent single-order'
      WHEN recency_days <= 90 THEN 'Needs attention'
      ELSE 'Inactive' END AS rfm_segment
FROM ranked
