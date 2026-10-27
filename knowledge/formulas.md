# Grounded formula reference

Formulas are definitions, not evaluated user code. A numerical answer still needs
a period/snapshot and guarded SQL. Ratios are fractions unless percent is requested.

## formula.aov
Name: AOV / มูลค่าเฉลี่ยต่อคำสั่งซื้อ
Formula: ยอดขายคำสั่งซื้อสำเร็จ ÷ จำนวนคำสั่งซื้อสำเร็จ
SQL expression: SUM(order_amount) / NULLIF(COUNT(*),0)
Source table: orders
Meaning: One row is one invoice; include anonymous invoices. GBP per invoice. Zero invoices gives NULL. AVG(order_amount) is equivalent on this non-null amount column.

## formula.repeat_rate
Name: repeat customer fraction / สัดส่วนลูกค้าซื้อซ้ำ
Formula: จำนวนผู้ซื้อที่มีรหัสและซื้ออย่างน้อย 2 ใบ ÷ ผู้ซื้อที่มีรหัสทั้งหมดในช่วงเดียวกัน
SQL expression: SUM(CASE WHEN invoice_frequency>=2 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0)
Source table: orders
Meaning: First filter period and customer_id IS NOT NULL, group original invoices by customer_id to create invoice_frequency. Keep one-order customers in the denominator. Not retention or repeat invoice fraction.

## formula.anonymous_share
Name: anonymous invoice fraction / สัดส่วนคำสั่งซื้อไม่มีรหัสลูกค้า
Formula: จำนวนคำสั่งซื้อไม่มีรหัสลูกค้า ÷ คำสั่งซื้อทั้งหมด
SQL expression: SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0)
Source table: orders
Meaning: Same period for numerator and denominator. This is invoice share, not customer share.

## formula.units_per_order
Name: units per order / จำนวนหน่วยเฉลี่ยต่อคำสั่งซื้อ
Formula: จำนวนหน่วยสินค้ารวมในคำสั่งซื้อสำเร็จ ÷ จำนวนคำสั่งซื้อสำเร็จ
SQL expression: AVG(total_units)
Source table: orders
Meaning: Units per invoice, distinct_products and product-line count are different quantities.

## formula.product_revenue
Name: product sale revenue / ยอดขายสินค้า
Formula: ผลรวมจำนวนหน่วย × ราคาต่อหน่วยของรายการ sale สำหรับสินค้าที่เลือก
SQL expression: SUM(line_amount)
Source table: sales_lines
Meaning: WHERE transaction_type='sale'. line_amount=quantity*unit_price. GBP; gross sale revenue, not profit or net refunded revenue. Weighted unit price = SUM(line_amount)/NULLIF(SUM(quantity),0).

## formula.mom_growth
Name: month-over-month sales growth / อัตราเติบโตยอดขายรายเดือน
Formula: (ยอดขายเดือนปัจจุบัน − ยอดขายเดือนก่อน) ÷ ยอดขายเดือนก่อน
SQL expression: (sales-LAG(sales) OVER (ORDER BY month)) / NULLIF(LAG(sales) OVER (ORDER BY month),0)
Source table: orders
Meaning: Aggregate sales by year-month first. First month or zero base gives NULL. Missing months require a calendar spine for calendar-month comparisons; LAG alone compares observed rows. Growth may be negative or greater than 1. Partial months need a warning.

## formula.country_share
Name: country sales share / สัดส่วนยอดขายแต่ละประเทศ
Formula: ยอดขายประเทศนั้น ÷ ยอดขายรวมทุกประเทศในช่วงเดียวกัน
SQL expression: sales / NULLIF(SUM(sales) OVER (),0)
Source table: orders
Meaning: First SUM(order_amount) by country; denominator covers every country in the same filtered population. Fraction, not percentage.

## formula.cumulative_sales
Name: cumulative sales / ยอดขายสะสม
Formula: ผลรวมยอดขายตั้งแต่ต้นช่วงถึงเดือนปัจจุบัน
SQL expression: SUM(sales) OVER (ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
Source table: orders
Meaning: Aggregate monthly SUM(order_amount) first. Filter the requested range before accumulating. For restarting by year use PARTITION BY YEAR(month).

## formula.moving_average
Name: three-month moving average / ค่าเฉลี่ยเคลื่อนที่ 3 เดือน
Formula: ค่าเฉลี่ยยอดขายเดือนปัจจุบันและสองเดือนก่อนที่มีข้อมูล
SQL expression: AVG(sales) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
Source table: orders
Meaning: Up to 3 observed monthly rows. First two windows have fewer rows. A calendar-complete moving average requires filling missing months explicitly and choosing a missing-month policy.

## formula.median_order
Name: approximate median order value / มัธยฐานมูลค่าคำสั่งซื้อโดยประมาณ
Formula: เปอร์เซ็นไทล์ที่ 50 โดยประมาณของมูลค่าคำสั่งซื้อ
SQL expression: PERCENTILE_APPROX(order_amount,0.5,10000)
Source table: orders
Meaning: Approximate, not exact median; GBP. Accuracy controls the approximation/memory tradeoff.

## formula.high_value_share
Name: high-value customer fraction / สัดส่วนลูกค้ามูลค่าสูง
Formula: จำนวนลูกค้า is_high_value=true ÷ ลูกค้าทั้งหมดใน snapshot เดียวกัน
SQL expression: SUM(CASE WHEN is_high_value THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0)
Source table: customer_summary
Meaning: Must select as_of_date. Project high-value flag uses the first CEIL(20%*population_size) ranked customers. Not a lifetime profitability prediction.

## formula.cancellation_share
Name: cancellation line fraction / สัดส่วนแถวรายการยกเลิก
Formula: จำนวนแถวสินค้าประเภท cancellation ÷ จำนวนแถวสินค้าทุกประเภทในช่วงเดียวกัน
SQL expression: SUM(CASE WHEN transaction_type='cancellation' THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0)
Source table: sales_lines
Meaning: All original product-line types remain in the denominator. Not an invoice cancellation rate and not a refund ratio.
