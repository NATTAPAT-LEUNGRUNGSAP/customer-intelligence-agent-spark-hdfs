# Versioned RAG evidence v2

## metric.sales
Completed sales / revenue / ยอดขาย = SUM(order_amount) from orders. Currency GBP. orders contains completed-sale invoices only; do not add a transaction_type column to orders. This is gross completed sales before returns, not profit or net sales. Use orders for country/month sales totals. Currency does not imply a country filter.

## metric.orders
Completed orders / invoices / จำนวนคำสั่งซื้อ / กี่ใบ = COUNT(*) from orders. One orders row is ONE INVOICE. A sales_lines row is ONE PRODUCT LINE, not an invoice. Never COUNT(*) from sales_lines to answer how many orders/invoices. Anonymous / unidentified / ไม่ระบุตัวตน orders are retained. ONLY when asked for anonymous orders alone, filter customer_id IS NULL. With no customer_id filter, COUNT(*) already includes both identified and anonymous invoices.

## metric.aov
AOV / average order value / เฉลี่ยต่อคำสั่งซื้อ = SUM(order_amount) / NULLIF(COUNT(*),0) from orders in the requested period. No customer_id filter means BOTH anonymous and identified orders are included; no extra NULL handling is required to include anonymous orders. Protect the DENOMINATOR count, not the numerator sum, from zero division. Do not average customer AOVs or product-line amounts to get overall order value.

## metric.customers
Identified purchasing customers / ลูกค้าที่ซื้อ = COUNT(DISTINCT customer_id) from orders in the requested period; NULL customer IDs are excluded. Count customers, not invoices or lines.

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
