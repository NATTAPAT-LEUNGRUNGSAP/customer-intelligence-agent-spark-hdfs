# ชุดคำถามพัฒนา: ไทย 100 / อังกฤษ 100

คำถามเรียบเรียงใหม่จาก schema ของ Online Retail II และรูปแบบวิเคราะห์ในเอกสาร Spark ไม่ใช่คำถามคัดลอก 200 ข้อจากเว็บไซต์ ชุดนี้เปิดเผยเพื่อพัฒนาระบบ จึงไม่ใช่ independent holdout.

80 คู่รัน SQL · 12 คู่ขอสูตรโดยไม่รัน · 8 คู่ต้องถามกลับ/แจ้งข้อมูลไม่รองรับ

| # | กลุ่ม | ภาษาไทย | English |
|---|---|---|---|
| 1 | scalar | เดือนมกราคม 2011 ยอดขายรวมเท่าไร | For January 2011, what is the total completed sales? |
| 2 | scalar | เดือนมกราคม 2011 จำนวนคำสั่งซื้อสำเร็จเท่าไร | For January 2011, what is the completed invoice count? |
| 3 | scalar | เดือนมกราคม 2011 มูลค่าเฉลี่ยต่อคำสั่งซื้อเท่าไร | For January 2011, what is the average order value? |
| 4 | scalar | เดือนมกราคม 2011 จำนวนลูกค้าที่ซื้อแบบไม่ซ้ำเท่าไร | For January 2011, what is the distinct purchasing customer count? |
| 5 | scalar | เดือนมกราคม 2011 จำนวนสินค้าที่ขายรวมในคำสั่งซื้อสำเร็จเท่าไร | For January 2011, what is the total units in completed invoices? |
| 6 | statistics | เดือนมกราคม 2011 มูลค่าคำสั่งซื้อสูงสุดเท่าไร | For January 2011, calculate the maximum invoice value. |
| 7 | statistics | เดือนมกราคม 2011 มูลค่าคำสั่งซื้อต่ำสุดเท่าไร | For January 2011, calculate the minimum invoice value. |
| 8 | statistics | เดือนมกราคม 2011 ส่วนเบี่ยงเบนมาตรฐานแบบตัวอย่างของมูลค่าคำสั่งซื้อเท่าไร | For January 2011, calculate the sample standard deviation of invoice value. |
| 9 | statistics | เดือนมกราคม 2011 มัธยฐานโดยประมาณของมูลค่าคำสั่งซื้อเท่าไร | For January 2011, calculate the approximate median invoice value. |
| 10 | statistics | เดือนมกราคม 2011 เปอร์เซ็นไทล์ที่ 90 โดยประมาณของมูลค่าคำสั่งซื้อเท่าไร | For January 2011, calculate the approximate 90th percentile of invoice value. |
| 11 | country | แสดงยอดขายแยกประเทศเดือนมกราคม 2011 เรียงชื่อประเทศ | For January 2011 show sales by country, ordered by country. |
| 12 | country | แสดงจำนวนคำสั่งซื้อแยกประเทศเดือนมกราคม 2011 เรียงชื่อประเทศ | For January 2011 show invoice count by country, ordered by country. |
| 13 | country | แสดงAOVแยกประเทศเดือนมกราคม 2011 เรียงชื่อประเทศ | For January 2011 show AOV by country, ordered by country. |
| 14 | country | แสดงจำนวนลูกค้าไม่ซ้ำแยกประเทศเดือนมกราคม 2011 เรียงชื่อประเทศ | For January 2011 show distinct purchasing customers by country, ordered by country. |
| 15 | country | แสดงจำนวนสินค้าที่ขายแยกประเทศเดือนมกราคม 2011 เรียงชื่อประเทศ | For January 2011 show units by country, ordered by country. |
| 16 | customer_ranking | ลูกค้าที่มีรหัส 5 อันดับแรกตามยอดขายเดือนมกราคม 2011 แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น | Rank the top 5 identified customers by sales in January 2011. Output customer ID and value; order value descending then customer ID ascending. |
| 17 | customer_ranking | ลูกค้าที่มีรหัส 5 อันดับแรกตามจำนวนคำสั่งซื้อเดือนมกราคม 2011 แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น | Rank the top 5 identified customers by invoice count in January 2011. Output customer ID and value; order value descending then customer ID ascending. |
| 18 | customer_ranking | ลูกค้าที่มีรหัส 5 อันดับแรกตามมูลค่าเฉลี่ยคำสั่งซื้อเดือนมกราคม 2011 แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น | Rank the top 5 identified customers by average invoice value in January 2011. Output customer ID and value; order value descending then customer ID ascending. |
| 19 | customer_ranking | ลูกค้าที่มีรหัส 5 อันดับแรกตามจำนวนสินค้าที่ซื้อเดือนมกราคม 2011 แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น | Rank the top 5 identified customers by units purchased in January 2011. Output customer ID and value; order value descending then customer ID ascending. |
| 20 | customer_ranking | ลูกค้าที่มีรหัส 5 อันดับแรกตามจำนวนสินค้าแตกต่างกันเฉลี่ยต่อใบเดือนมกราคม 2011 แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น | Rank the top 5 identified customers by mean distinct products per invoice in January 2011. Output customer ID and value; order value descending then customer ID ascending. |
| 21 | product_ranking | สินค้า 5 อันดับตามยอดขายเดือนมกราคม 2011 ใช้เฉพาะรายการ sale แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น | For January 2011 rank top 5 product IDs by sale revenue, using only sale lines. Output product ID and value; order value descending then product ID ascending. |
| 22 | product_ranking | สินค้า 5 อันดับตามจำนวนหน่วยเดือนมกราคม 2011 ใช้เฉพาะรายการ sale แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น | For January 2011 rank top 5 product IDs by sale units, using only sale lines. Output product ID and value; order value descending then product ID ascending. |
| 23 | product_ranking | สินค้า 5 อันดับตามจำนวนรายการขายเดือนมกราคม 2011 ใช้เฉพาะรายการ sale แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น | For January 2011 rank top 5 product IDs by sale product-line count, using only sale lines. Output product ID and value; order value descending then product ID ascending. |
| 24 | product_ranking | สินค้า 5 อันดับตามราคาขายต่อหน่วยเฉลี่ยแบบถ่วงน้ำหนักเดือนมกราคม 2011 ใช้เฉพาะรายการ sale แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น | For January 2011 rank top 5 product IDs by quantity-weighted sale unit price, using only sale lines. Output product ID and value; order value descending then product ID ascending. |
| 25 | product_ranking | สินค้า 5 อันดับตามจำนวนลูกค้าที่มีรหัสไม่ซ้ำเดือนมกราคม 2011 ใช้เฉพาะรายการ sale แสดงรหัสและค่า เรียงค่าลดลงแล้วรหัสเพิ่มขึ้น | For January 2011 rank top 5 product IDs by distinct identified purchasing customers, using only sale lines. Output product ID and value; order value descending then product ID ascending. |
| 26 | monthly | แสดงยอดขายรายเดือนตลอดปี 2011 แยกปีเดือน เรียงเดือน | Show monthly sales for calendar year 2011, grouped by year-month and ordered by month. |
| 27 | monthly | แสดงจำนวนคำสั่งซื้อรายเดือนตลอดปี 2011 แยกปีเดือน เรียงเดือน | Show monthly invoice count for calendar year 2011, grouped by year-month and ordered by month. |
| 28 | monthly | แสดงAOVรายเดือนตลอดปี 2011 แยกปีเดือน เรียงเดือน | Show monthly AOV for calendar year 2011, grouped by year-month and ordered by month. |
| 29 | monthly | แสดงจำนวนลูกค้าไม่ซ้ำรายเดือนตลอดปี 2011 แยกปีเดือน เรียงเดือน | Show monthly distinct purchasing customers for calendar year 2011, grouped by year-month and ordered by month. |
| 30 | monthly | แสดงจำนวนสินค้าที่ขายรายเดือนตลอดปี 2011 แยกปีเดือน เรียงเดือน | Show monthly units sold for calendar year 2011, grouped by year-month and ordered by month. |
| 31 | transaction_types | เดือนมกราคม 2011 มีรายการสินค้าประเภท sale (ขาย) กี่แถว | Count original product lines classified as sale in January 2011. |
| 32 | transaction_types | เดือนมกราคม 2011 มีรายการสินค้าประเภท cancellation (ยกเลิก) กี่แถว | Count original product lines classified as cancellation in January 2011. |
| 33 | transaction_types | เดือนมกราคม 2011 มีรายการสินค้าประเภท return (คืนสินค้า) กี่แถว | Count original product lines classified as return in January 2011. |
| 34 | transaction_types | เดือนมกราคม 2011 มีรายการสินค้าประเภท adjustment (ปรับปรุง) กี่แถว | Count original product lines classified as adjustment in January 2011. |
| 35 | transaction_types | เดือนมกราคม 2011 มีรายการสินค้าประเภท invalid (ไม่ถูกต้อง) กี่แถว | Count original product lines classified as invalid in January 2011. |
| 36 | snapshot_counts | ณ snapshot 2011-12-01 นับลูกค้าทั้งหมด | At snapshot 2011-12-01 count all customers. |
| 37 | snapshot_counts | ณ snapshot 2011-12-01 นับลูกค้ามูลค่าสูง | At snapshot 2011-12-01 count high-value customers. |
| 38 | snapshot_counts | ณ snapshot 2011-12-01 นับลูกค้า Champions | At snapshot 2011-12-01 count Champions. |
| 39 | snapshot_counts | ณ snapshot 2011-12-01 นับลูกค้า Inactive | At snapshot 2011-12-01 count Inactive customers. |
| 40 | snapshot_counts | ณ snapshot 2011-12-01 นับลูกค้าที่เป็นทั้ง Champions และ high-value | At snapshot 2011-12-01 count customers who are both Champions and high-value. |
| 41 | segment_statistics | ณ snapshot 2011-12-01 แสดงrecency เฉลี่ยแยก rfm_segment เรียงชื่อกลุ่ม | At snapshot 2011-12-01 show mean recency days by rfm_segment, ordered by segment. |
| 42 | segment_statistics | ณ snapshot 2011-12-01 แสดงจำนวนคำสั่งซื้อ 180 วันเฉลี่ยแยก rfm_segment เรียงชื่อกลุ่ม | At snapshot 2011-12-01 show mean 180-day order count by rfm_segment, ordered by segment. |
| 43 | segment_statistics | ณ snapshot 2011-12-01 แสดงยอดซื้อ 180 วันรวมแยก rfm_segment เรียงชื่อกลุ่ม | At snapshot 2011-12-01 show total 180-day sales by rfm_segment, ordered by segment. |
| 44 | segment_statistics | ณ snapshot 2011-12-01 แสดงAOV ของลูกค้าเฉลี่ยแบบไม่ถ่วงน้ำหนักแยก rfm_segment เรียงชื่อกลุ่ม | At snapshot 2011-12-01 show unweighted mean of customer AOV by rfm_segment, ordered by segment. |
| 45 | segment_statistics | ณ snapshot 2011-12-01 แสดงจำนวนลูกค้าในแต่ละกลุ่ม RFMแยก rfm_segment เรียงชื่อกลุ่ม | At snapshot 2011-12-01 show customer count by rfm_segment, ordered by segment. |
| 46 | basket | เดือนมกราคม 2011 คำนวณจำนวนหน่วยเฉลี่ยต่อคำสั่งซื้อ | For January 2011 calculate the mean units per invoice. |
| 47 | basket | เดือนมกราคม 2011 คำนวณจำนวนสินค้าต่างชนิดเฉลี่ยต่อคำสั่งซื้อ | For January 2011 calculate the mean distinct products per invoice. |
| 48 | basket | เดือนมกราคม 2011 คำนวณจำนวนคำสั่งซื้อที่มีหน่วยสินค้ามากกว่า 20 | For January 2011 calculate the count of invoices with more than 20 units. |
| 49 | basket | เดือนมกราคม 2011 คำนวณจำนวนคำสั่งซื้อที่มีสินค้าอย่างน้อย 5 ชนิด | For January 2011 calculate the count of invoices with at least 5 distinct products. |
| 50 | basket | เดือนมกราคม 2011 คำนวณสัดส่วนคำสั่งซื้อที่มีสินค้าชนิดเดียว ไม่ใช่เปอร์เซ็นต์ | For January 2011 calculate the fraction of single-product invoices, not a percentage. |
| 51 | repeat_rate | สัดส่วนลูกค้าที่มีรหัสและซื้อซ้ำอย่างน้อย 2 ใบในเดือนมกราคม 2011 ประเทศ United Kingdom เท่าไร แสดงเป็น fraction | In United Kingdom in January 2011, calculate the repeat customer fraction: identified customers with at least two invoices divided by all identified purchasing customers. |
| 52 | repeat_rate | สัดส่วนลูกค้าที่มีรหัสและซื้อซ้ำอย่างน้อย 2 ใบในเดือนมกราคม 2011 ประเทศ France เท่าไร แสดงเป็น fraction | In France in January 2011, calculate the repeat customer fraction: identified customers with at least two invoices divided by all identified purchasing customers. |
| 53 | repeat_rate | สัดส่วนลูกค้าที่มีรหัสและซื้อซ้ำอย่างน้อย 2 ใบในเดือนมกราคม 2011 ประเทศ Germany เท่าไร แสดงเป็น fraction | In Germany in January 2011, calculate the repeat customer fraction: identified customers with at least two invoices divided by all identified purchasing customers. |
| 54 | repeat_rate | สัดส่วนลูกค้าที่มีรหัสและซื้อซ้ำอย่างน้อย 2 ใบในเดือนมกราคม 2011 ประเทศ Spain เท่าไร แสดงเป็น fraction | In Spain in January 2011, calculate the repeat customer fraction: identified customers with at least two invoices divided by all identified purchasing customers. |
| 55 | repeat_rate | สัดส่วนลูกค้าที่มีรหัสและซื้อซ้ำอย่างน้อย 2 ใบในเดือนมกราคม 2011 ประเทศ Netherlands เท่าไร แสดงเป็น fraction | In Netherlands in January 2011, calculate the repeat customer fraction: identified customers with at least two invoices divided by all identified purchasing customers. |
| 56 | ratios | เดือนมกราคม 2011 คำนวณสัดส่วนคำสั่งซื้อที่ไม่มีรหัสลูกค้า แสดงเป็นสัดส่วนไม่คูณ 100 | For January 2011 calculate anonymous invoice fraction. Return a fraction, not multiplied by 100. |
| 57 | ratios | เดือนมกราคม 2011 คำนวณสัดส่วนยอดขายจากคำสั่งซื้อที่ไม่มีรหัสลูกค้า แสดงเป็นสัดส่วนไม่คูณ 100 | For January 2011 calculate anonymous invoice sales share. Return a fraction, not multiplied by 100. |
| 58 | ratios | เดือนมกราคม 2011 คำนวณยอดขายต่อผู้ซื้อที่มีรหัสหนึ่งคน โดยตัดคำสั่งซื้อไม่มีรหัสออกทั้งเศษและส่วน แสดงเป็นสัดส่วนไม่คูณ 100 | For January 2011 calculate sales per identified purchasing customer excluding anonymous invoices from numerator and denominator. Return a fraction, not multiplied by 100. |
| 59 | ratios | เดือนมกราคม 2011 คำนวณจำนวนคำสั่งซื้อเฉลี่ยต่อผู้ซื้อที่มีรหัส โดยตัดคำสั่งซื้อไม่มีรหัสออก แสดงเป็นสัดส่วนไม่คูณ 100 | For January 2011 calculate invoice frequency per identified purchasing customer excluding anonymous invoices. Return a fraction, not multiplied by 100. |
| 60 | ratios | เดือนมกราคม 2011 คำนวณสัดส่วนคำสั่งซื้อที่ยอดมากกว่า 100 GBP แสดงเป็นสัดส่วนไม่คูณ 100 | For January 2011 calculate fraction of invoices above 100 GBP. Return a fraction, not multiplied by 100. |
| 61 | windows | แสดงรายเดือนปี 2011 พร้อมยอดขายสะสมตั้งแต่ต้นปี แสดงเฉพาะเดือนและค่าที่ขอ เรียงเดือน | For each month of 2011 show year-to-date cumulative sales. Output only month and the requested value, ordered by month. |
| 62 | windows | แสดงรายเดือนปี 2011 พร้อมค่าเฉลี่ยเคลื่อนที่ยอดขาย 3 เดือนที่มีข้อมูล รวมเดือนปัจจุบัน แสดงเฉพาะเดือนและค่าที่ขอ เรียงเดือน | For each month of 2011 show 3-observed-month trailing moving average including current month. Output only month and the requested value, ordered by month. |
| 63 | windows | แสดงรายเดือนปี 2011 พร้อมยอดขายเดือนก่อนหน้า โดยเดือนแรกเป็น NULL แสดงเฉพาะเดือนและค่าที่ขอ เรียงเดือน | For each month of 2011 show previous observed month sales, NULL for first month. Output only month and the requested value, ordered by month. |
| 64 | windows | แสดงรายเดือนปี 2011 พร้อมการเปลี่ยนแปลงยอดขายจากเดือนก่อนหน้าเป็นจำนวนเงิน โดยเดือนแรกเป็น NULL แสดงเฉพาะเดือนและค่าที่ขอ เรียงเดือน | For each month of 2011 show sales change from previous observed month in GBP, NULL for first month. Output only month and the requested value, ordered by month. |
| 65 | windows | แสดงรายเดือนปี 2011 พร้อมอัตราเติบโตยอดขายเทียบเดือนก่อนหน้าเป็น fraction เดือนแรกหรือฐานศูนย์เป็น NULL แสดงเฉพาะเดือนและค่าที่ขอ เรียงเดือน | For each month of 2011 show month-over-month sales growth as a fraction, NULL for first month or zero base. Output only month and the requested value, ordered by month. |
| 66 | time_buckets | ปี 2011 แสดงจำนวนคำสั่งซื้อรายวันเดือนมกราคม เรียงเวลา | Show invoice counts daily during January 2011, ordered by time. |
| 67 | time_buckets | ปี 2011 แสดงจำนวนคำสั่งซื้อรายชั่วโมงของวันที่ 5 มกราคม เรียงเวลา | Show invoice counts hourly during January 5 2011, ordered by time. |
| 68 | time_buckets | ปี 2011 แสดงจำนวนคำสั่งซื้อรายไตรมาส เรียงเวลา | Show invoice counts quarterly 2011, ordered by time. |
| 69 | time_buckets | แสดงจำนวนคำสั่งซื้อรายปีตลอดข้อมูลทั้งหมดทุกปี เรียงเวลา | Show invoice counts yearly over all available data, ordered by time. |
| 70 | time_buckets | ปี 2011 แสดงจำนวนคำสั่งซื้อรายสัปดาห์เดือนมกราคม เรียงเวลา | Show invoice counts weekly during January 2011, ordered by time. |
| 71 | snapshot_activity | ณ snapshot 2011-12-01 หาวันซื้อที่พบครั้งแรกต่ำสุด | At snapshot 2011-12-01 find the earliest observed first purchase date. |
| 72 | snapshot_activity | ณ snapshot 2011-12-01 หาวันซื้อครั้งล่าสุดสูงสุด | At snapshot 2011-12-01 find the latest observed purchase date. |
| 73 | snapshot_activity | ณ snapshot 2011-12-01 หาrecency สูงสุด | At snapshot 2011-12-01 find the maximum recency days. |
| 74 | snapshot_activity | ณ snapshot 2011-12-01 หาจำนวนลูกค้าที่มีคำสั่งซื้อ 180 วันอย่างน้อย 10 ใบ | At snapshot 2011-12-01 find the number of customers with at least 10 invoices in 180 days. |
| 75 | snapshot_activity | ณ snapshot 2011-12-01 หาจำนวนลูกค้าที่เป็น Inactive และไม่ใช่ high-value | At snapshot 2011-12-01 find the number of Inactive customers who are not high-value. |
| 76 | monthly_max | เดือนไหนออเดอร์เยอะสุด | Which month had the most orders? |
| 77 | country_share | เดือนมกราคม 2011 แสดงแต่ละประเทศกับสัดส่วนยอดขายต่อยอดรวม เรียงประเทศ | For January 2011 show each country and its fraction of total sales, ordered by country. |
| 78 | having | เดือนมกราคม 2011 มีลูกค้าที่มีรหัสอย่างน้อย 3 คำสั่งซื้อกี่คน | How many identified customers placed at least three invoices in January 2011? |
| 79 | line_quality | เดือนมกราคม 2011 แสดงจำนวนแถวสินค้าแยก transaction_type เรียงประเภท | For January 2011 show product-line counts by transaction_type, ordered by type. |
| 80 | high_value_fraction | ณ snapshot 2011-12-01 ลูกค้า high-value เป็นสัดส่วนเท่าไรของลูกค้าทั้งหมด | At snapshot 2011-12-01 what fraction of customers are high-value? |
| 81 | formula | ขอสูตรAOV ไม่ต้องรัน SQL | Explain the formula for AOV; do not execute SQL. |
| 82 | formula | ขอสูตรสัดส่วนลูกค้าซื้อซ้ำ ไม่ต้องรัน SQL | Explain the formula for repeat customer fraction; do not execute SQL. |
| 83 | formula | ขอสูตรสัดส่วนคำสั่งซื้อไม่มีรหัสลูกค้า ไม่ต้องรัน SQL | Explain the formula for anonymous invoice fraction; do not execute SQL. |
| 84 | formula | ขอสูตรจำนวนหน่วยเฉลี่ยต่อคำสั่งซื้อ ไม่ต้องรัน SQL | Explain the formula for units per order; do not execute SQL. |
| 85 | formula | ขอสูตรยอดขายสินค้า ไม่ต้องรัน SQL | Explain the formula for product sale revenue; do not execute SQL. |
| 86 | formula | ขอสูตรอัตราเติบโตยอดขายรายเดือน ไม่ต้องรัน SQL | Explain the formula for month-over-month sales growth; do not execute SQL. |
| 87 | formula | ขอสูตรสัดส่วนยอดขายแต่ละประเทศ ไม่ต้องรัน SQL | Explain the formula for country sales share; do not execute SQL. |
| 88 | formula | ขอสูตรยอดขายสะสม ไม่ต้องรัน SQL | Explain the formula for cumulative sales; do not execute SQL. |
| 89 | formula | ขอสูตรค่าเฉลี่ยเคลื่อนที่ 3 เดือน ไม่ต้องรัน SQL | Explain the formula for three-month moving average; do not execute SQL. |
| 90 | formula | ขอสูตรมัธยฐานมูลค่าคำสั่งซื้อโดยประมาณ ไม่ต้องรัน SQL | Explain the formula for approximate median order value; do not execute SQL. |
| 91 | formula | ขอสูตรสัดส่วนลูกค้ามูลค่าสูง ไม่ต้องรัน SQL | Explain the formula for high-value customer fraction; do not execute SQL. |
| 92 | formula | ขอสูตรสัดส่วนแถวรายการยกเลิก ไม่ต้องรัน SQL | Explain the formula for cancellation line fraction; do not execute SQL. |
| 93 | clarification | ยอดขายรวมเท่าไร | What is total revenue? |
| 94 | clarification | ลูกค้าดีที่สุดคือใคร | Who are our best customers? |
| 95 | clarification | แสดงกลุ่มลูกค้า RFM | Show RFM segments. |
| 96 | clarification | นับลูกค้ามูลค่าสูง | Count high-value customers. |
| 97 | clarification | แสดงกลุ่ม RFM ณ snapshot 2011-11-30 | Show RFM segments at snapshot 2011-11-30. |
| 98 | clarification | กำไรเดือนมกราคม 2011 เท่าไร | What was profit in January 2011? |
| 99 | clarification | ยอดขายเดือนมกราคม 2024 เท่าไร | What were sales in January 2024? |
| 100 | clarification | วัดผลแคมเปญในปี 2011 | Measure campaign uplift in 2011. |

แหล่งอ้างอิงการออกแบบ:
- [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii)
- [Spark built-in functions](https://spark.apache.org/docs/4.1.3/sql-ref-functions-builtin.html)
- [Spark window functions](https://spark.apache.org/docs/4.1.3/sql-ref-syntax-qry-select-window.html)

Gold SQL อยู่เฉพาะ evaluation/ ไม่ถูกโหลดเข้า Agent หรือ RAG; ตัวอย่าง syntax ใน knowledge/ เป็นรูปแบบทั่วไป ไม่ใช่คลังคำตอบของแต่ละข้อ.
