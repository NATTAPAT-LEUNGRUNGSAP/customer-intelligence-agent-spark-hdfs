# Reusable analytical syntax

Examples below are composable expressions, not stored answers to evaluation questions.
Sources: https://spark.apache.org/docs/4.1.3/sql-ref-functions-builtin.html and
https://spark.apache.org/docs/4.1.3/sql-ref-syntax-qry-select-window.html

## syntax.statistics
Statistics / สถิติ / มัธยฐาน / เปอร์เซ็นไทล์ / ส่วนเบี่ยงเบน: apply MIN(x), MAX(x), STDDEV(x) for sample standard deviation; PERCENTILE_APPROX(x,0.5,10000) for approximate median, or 0.9 for p90. Use order_amount from orders for invoice value, never customer_summary.aov_180d. Approximate percentiles are explicitly approximate; accuracy is not a business confidence interval. Return only requested statistic columns. All completed invoices include anonymous buyers unless excluded by the question.

## syntax.basket
Basket / ตะกร้า / หน่วยต่อใบ: orders.total_units is the unit count in one completed invoice; distinct_products is number of different product IDs in that invoice. AVG(total_units) means units per invoice. AVG(distinct_products) is different. Conditional count: SUM(CASE WHEN distinct_products=1 THEN 1 ELSE 0 END). Conditional fraction: conditional count / NULLIF(COUNT(*),0). A unit count is not a count of product lines or distinct products.

## syntax.transactions
Transaction types / ประเภทธุรกรรม: sales_lines has sale, cancellation, return, adjustment, invalid. COUNT(*) counts ORIGINAL product lines, not invoices; filter the requested type exactly. For a breakdown, GROUP BY transaction_type without a type filter. Orders already contain completed-sale invoices only. Never assume cancellation amount is realized refunded cash. Do not combine a cancellation-line count with an invoice denominator. Data-quality counts are not customer metrics.

## syntax.ratios
Ratios / share / fraction / สัดส่วน: use numerator / NULLIF(denominator,0); return NULL for an empty/zero denominator. Multiply by 100 ONLY for explicitly requested percent. For anonymous invoice share count customer_id IS NULL over all invoice rows, not all customers. For country sales share first aggregate by country, then sales / NULLIF(SUM(sales) OVER (),0). A share of positive sales is 0..1; growth can be negative or exceed 1 and must not be constrained as a share. Sales per identified customer must exclude anonymous invoices from numerator as well as denominator.
Two-stage syntax on grouped values: WITH grouped AS (SELECT group_key, SUM(amount) AS group_value FROM allowed_view GROUP BY group_key) SELECT group_key, group_value/NULLIF(SUM(group_value) OVER (),0) FROM grouped. These names are placeholders: replace with actual schema and apply the requested time filter inside grouped. Do not GROUP BY country and simultaneously window SUM(raw order_amount): the raw amount is not a grouped value. Use a CTE, or SUM(SUM(order_amount)) OVER () on already grouped sums.

## syntax.windows
Window / cumulative / moving average / growth / ยอดสะสม / เคลื่อนที่ / เติบโต: first aggregate transactions to one calendar year-month, then calculate windows in a CTE. SUM(value) OVER (ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) is cumulative. AVG(value) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) is a trailing mean of up to 3 observed rows, NOT a calendar-complete 3-month series. LAG(value) OVER (ORDER BY month) yields previous observed month. Growth fraction = (value-previous)/NULLIF(previous,0), first month NULL. Do not LAG raw invoice rows for monthly growth. Preserve the year in the month bucket. Output only columns requested. Snapshot filters are irrelevant for orders.

## syntax.having
Aggregate filtering / HAVING / อย่างน้อย: filter raw time/country/population in WHERE, GROUP BY customer_id, then HAVING COUNT(*)>=threshold. To count eligible customers, wrap these groups in a CTE and COUNT(*) outside. Do not COUNT(DISTINCT customer_id) before calculating invoice frequency. Identified customers require customer_id IS NOT NULL before grouping.

## syntax.monthly_extrema
Highest month / เดือนไหน / ออเดอร์เยอะสุด: aggregate orders by DATE_TRUNC('MONTH',order_ts), preserving year. Count invoices with COUNT(*). To retain ties compare aggregated count to MAX(count), or use RANK/DENSE_RANK ordered only by count DESC. ROW_NUMBER, a month tiebreaker inside ranking, or LIMIT 1 loses ties. Sort the final tied results by month. For explicitly supplied whole-data scope use all loaded orders without an invented time filter; the manifest maximum timestamp is inclusive. Partial first/last months are not equivalent to complete months.

## syntax.snapshot_statistics
Snapshot descriptive statistics / recency / 180 วัน: customer_summary has one identified customer per as_of_date. Select the available snapshot before aggregating. AVG(aov_180d) is an unweighted average of customer AOVs, NOT the overall transaction AOV. SUM(sales_180d) is sales for the snapshot population in its 180-day window. First_purchase_date is first observed purchase, not acquisition or lifetime history. High-value and RFM segments can overlap.

## syntax.product_metrics
Product ranking / จัดอันดับสินค้า: output product_id and the requested metric only, not description. Group by product_id, never product_id+description unless asked. Sale product-line count / จำนวนรายการขาย = COUNT(*) on sale lines, different from sale units = SUM(quantity). Sale revenue = SUM(line_amount). Quantity-weighted unit price / ราคาต่อหน่วยถ่วงน้ำหนัก = SUM(line_amount)/NULLIF(SUM(quantity),0), not SUM(line_amount) alone or AVG(unit_price). Distinct purchasing customers = COUNT(DISTINCT customer_id). Use the requested measure, not a substitute, and a deterministic product_id tie break.
