# Versioned RAG evidence v2

## metric.sales
Completed sales / revenue / ยอดขาย = SUM(order_amount) from orders. Currency GBP. orders contains completed-sale invoices only; do not add a transaction_type column to orders. This is gross completed sales before returns, not profit or net sales. Use orders for country/month sales totals. Currency does not imply a country filter.

## metric.orders
Completed orders / invoices / จำนวนคำสั่งซื้อ / กี่ใบ = COUNT(*) from orders. One orders row is ONE INVOICE. A sales_lines row is ONE PRODUCT LINE, not an invoice. Never COUNT(*) from sales_lines to answer how many orders/invoices. Anonymous / unidentified / ไม่ระบุตัวตน orders are retained. ONLY when asked for anonymous orders alone, filter customer_id IS NULL. With no customer_id filter, COUNT(*) already includes both identified and anonymous invoices.

## metric.aov
AOV / average order value / เฉลี่ยต่อคำสั่งซื้อ = SUM(order_amount) / NULLIF(COUNT(*),0) from orders in the requested period. No customer_id filter means BOTH anonymous and identified orders are included; no extra NULL handling is required to include anonymous orders. Protect the DENOMINATOR count, not the numerator sum, from zero division. Do not average customer AOVs or product-line amounts to get overall order value.
If explicitly asked for the unweighted MEAN OF CUSTOMER AOVs at a snapshot, use AVG(customer_summary.aov_180d) for that snapshot, optionally grouped by rfm_segment. That is a different, explicitly requested metric; do not replace it with transactional AVG(order_amount). Units per invoice and distinct products per invoice are not monetary AOV.

## metric.customers
Identified purchasing customers / ลูกค้าที่ซื้อ / ลูกค้าไม่ซ้ำ / จำนวนลูกค้าที่ซื้อแบบไม่ซ้ำ = COUNT(DISTINCT customer_id) from orders in the requested period; NULL customer IDs are excluded by COUNT(DISTINCT) itself. Count customers, not invoices or lines. Thai ไม่ซ้ำ means unique/distinct IDs, NOT customers with exactly one invoice or non-repeat customers. Do not add frequency=1 or HAVING COUNT(*)=1. For a country breakdown retain all countries from the requested invoices, including zero identified buyers; do not remove anonymous rows with WHERE unless an explicitly identified-only invoice population is requested.
For product-specific distinct purchasing customers, read sales_lines filtered transaction_type='sale' and GROUP BY product_id with COUNT(DISTINCT customer_id). The generic orders view has no product_id; do not use it for product-specific buyer rankings.

## metric.invoice_share
Invoice fraction / สัดส่วนคำสั่งซื้อ counts invoices, not money. Numerator = invoices satisfying the requested condition; denominator = ALL invoices in the same time/country population. Use SUM(CASE WHEN condition THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0) on orders, or AVG of a 1/0 indicator. Anonymous fraction condition is customer_id IS NULL; high-amount invoice fraction condition is order_amount > requested threshold; single-product invoice fraction condition is distinct_products=1. Keep these conditions OUT of WHERE: filtering them removes the denominator population and incorrectly returns 1. Time/country WHERE filters still apply to both. A SUM of money over a SUM of money is a sales share, not an invoice fraction.

## metric.units
Sold/purchased units / จำนวนสินค้าที่ขาย / จำนวนสินค้าที่ซื้อ means unit quantity, not money or number of different product IDs. On completed invoices use SUM(orders.total_units); for mean units per invoice use AVG(total_units). Customer rankings by purchased units aggregate total_units by customer_id, excluding NULL IDs. A product-specific ranking uses SUM(sales_lines.quantity) filtered transaction_type='sale'. Do not SUM(order_amount) for units. Basket variety is AVG(orders.distinct_products) when asked mean distinct products per invoice, not AVG(total_units) and not monetary AOV.

## metric.purchase_frequency
Average invoice frequency per identified purchasing customer / จำนวนคำสั่งซื้อเฉลี่ยต่อผู้ซื้อที่มีรหัส = COUNT(*) / NULLIF(COUNT(DISTINCT customer_id),0) from orders WHERE customer_id IS NOT NULL in the requested period. Return one scalar population average, not a list of customer frequencies. This is invoices per buyer, not monetary AOV or repeat-customer fraction. Never use SUM(order_amount) as the numerator for frequency.

## metric.spend_per_customer
Sales per identified purchasing customer / ยอดขายต่อผู้ซื้อที่มีรหัส = SUM(order_amount) / NULLIF(COUNT(DISTINCT customer_id),0) from orders WHERE customer_id IS NOT NULL in the requested period. Return one scalar GBP-per-buyer average. Filter anonymous invoices out of BOTH numerator and denominator. This is not invoice AOV; the denominator is distinct buyers, not COUNT(*).

## metric.repeat_rate
Repeat customer rate / ลูกค้าซื้อซ้ำ is a FRACTION in the requested transaction period. First filter orders to that period and customer_id IS NOT NULL, retaining ORIGINAL invoice rows. Group once by customer_id and COUNT(*) as order_count. From that FULL per-customer frequency table, numerator = SUM(CASE WHEN order_count>=2 THEN 1 ELSE 0 END), denominator = COUNT(*) of ALL purchasing customers including one-order customers. Use NULLIF on the denominator. Do not INNER JOIN the population to the repeat-only subset: that incorrectly removes one-order customers and can force a rate of 1.0. Do not DISTINCT customer_id BEFORE counting original invoices; DISTINCT after frequencies are computed can be valid, but is unnecessary with the simple frequency-table aggregation. This is not cohort retention or a snapshot metric; do not use customer_summary for arbitrary periods.

## metric.high_value
High-value / มูลค่าสูง customers: customer_summary.is_high_value = true at the requested snapshot. This is the first CEIL(20% * population_size) customers ranked by sales_180d DESC, then customer_id ASC. High value and RFM segment are INDEPENDENT dimensions that CAN overlap; a customer can be BOTH Champions and high-value, or Inactive and high-value. If the question asks for both, combine the two filters with AND. Do not substitute one label for the other or add an unrequested filter. Fraction = high-value count / population count. Use the requested available as_of_date.

## segment.champions
Champions / แชมเปี้ยน is customer_summary.rfm_segment = 'Champions' at the requested snapshot. Definition: recency_days <=30 and orders_180d >=3. Count customer_summary rows with rfm_segment='Champions'. High-value is a separate INDEPENDENT flag that CAN be true for a Champion. If BOTH are requested, use rfm_segment='Champions' AND is_high_value=true. These are not mutually exclusive categories. Do not add the high-value filter when only Champions are requested.

## segment.inactive
Inactive / ไม่เคลื่อนไหว is customer_summary.rfm_segment = 'Inactive' at the requested snapshot. Definition: recency_days >90 within the eligible 180-day purchasing population. When the user asks only for Inactive, include BOTH high-value and non-high-value customers; do not add an UNREQUESTED is_high_value=false filter. If the user explicitly requests Inactive AND NOT high-value, combine rfm_segment='Inactive' AND is_high_value=false. If explicitly high-value Inactive, combine rfm_segment='Inactive' AND is_high_value=true. The dimensions are independent; honor the requested intersection or exclusion.

## segment.distribution
RFM segment / กลุ่มลูกค้า distribution groups customer_summary by rfm_segment for one as_of_date. Segments: Champions (recency<=30, frequency>=3); Recent repeat (recency<=30, frequency=2); Recent single-order (recency<=30, frequency=1); Needs attention (recency 31..90); Inactive (recency>90 within the eligible population). These are project definitions. Frequency is invoices, monetary is 180-day sales. Do not infer other snapshot distributions.
