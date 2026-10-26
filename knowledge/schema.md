# Versioned RAG evidence v2

## schema.orders
orders: one consistent COMPLETED-SALE INVOICE per row. invoice_id/customer_id/country strings; order_ts timestamp; order_amount decimal; total_units bigint; distinct_products bigint. Use for invoice counts, completed sales, AOV, purchasing customers, repeat rates. Anonymous customer_id NULL invoices are retained. Mixed customer/country invoices are excluded and counted in the build report. No transaction_type column exists in orders.

## schema.sales_lines
sales_lines: one ORIGINAL PRODUCT LINE per row; never one invoice per row. invoice_id/customer_id/product_id strings; description string; invoice_ts timestamp; country string; quantity bigint; unit_price decimal; line_amount decimal; transaction_type string; source_sheet string; source_row bigint. Types are sale, cancellation, return, adjustment, invalid; 'completed' is NOT a type. For product revenue/units use transaction_type='sale', then sum line_amount/quantity. For cancellation / ยกเลิก lines use 'cancellation'; for return / คืนสินค้า lines use 'return'.

## schema.customer_summary
customer_summary: one IDENTIFIED CUSTOMER in the 180-day window for one snapshot. customer_id string; first_purchase_date/last_purchase_date/as_of_date dates; recency_days int; orders_180d bigint; sales_180d/aov_180d decimal; monetary_rank/population_size bigint; is_high_value boolean; rfm_segment string. Anonymous customers and those without a purchase in the window are excluded. first_purchase_date is first OBSERVED, not necessarily first-ever purchase.

## schema.joins
Joining product lines to orders repeats order_amount per product line: never SUM the repeated invoice amount. Select the snapshot before joining customer_summary to orders by customer_id. Prefer a single table when it already contains the requested facts.
