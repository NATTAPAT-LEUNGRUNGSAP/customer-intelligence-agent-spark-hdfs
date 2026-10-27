# Versioned RAG evidence v2

## syntax.time
Time period / ช่วงเวลา: transaction ranges include start and exclude end. Use timestamp comparisons on order_ts for orders, invoice_ts for sales_lines. January through March ends at April 1, exclusive. Use date_trunc('MONTH', timestamp_column) for monthly grouping; order by month ascending. Source timezone is unspecified; UTC session is a processing convention only.
For execution use direct half-open WHERE comparisons with typed full TIMESTAMP literals at midnight; keep DATE_TRUNC for grouping. Never add an amount, country or customer filter unless asked. Spark DATE_TRUNC returns a timestamp, not a month-name string.

## syntax.aggregation
Use GROUP BY for customer, product or country aggregation. Conditional aggregation: SUM(CASE WHEN condition THEN 1 ELSE 0 END). Division: numerator / NULLIF(denominator,0). For repeat-customer rate group original orders by customer BEFORE aggregating frequencies. COUNT(DISTINCT customer_id) excludes NULL; COUNT(*) includes anonymous invoice rows.

## syntax.ranking
Top N needs explicit ORDER BY metric DESC followed by an ascending deterministic ID/country tie break, then LIMIT N. row_number(), rank(), lag() and lead() are allowed read-only analytics functions. Generate SQL for the question: these are not query templates.
