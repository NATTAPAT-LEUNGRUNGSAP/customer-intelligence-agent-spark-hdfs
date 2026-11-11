import sys,json,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from metric_contracts import validate_metric_expression,request_constraints
from result_contracts import validate_semantics,result_violations
from semantic_contracts import validate_business_sql
from sql_guard import validate_sql
from dataset_info import requested_schema, column_overview
ROOT=Path(__file__).resolve().parents[1]
class AggregationAnswerabilityTests(unittest.TestCase):
    def test_schema_question_lists_loaded_public_columns_without_sql(self):
        tables = requested_schema('มีคอลัมน์ชื่ออะไรบ้างในฐานข้อมูล')
        schema = {'orders': 'struct<order_amount:decimal(18,4),invoice_id:string>',
                  'internal': 'struct<secret:string>'}
        info = column_overview(schema, tables, 'มีคอลัมน์ชื่ออะไรบ้างในฐานข้อมูล')
        self.assertEqual(info['result']['rows'],
                         [['orders', 'order_amount', 'decimal(18,4)'], ['orders', 'invoice_id', 'string']])
        self.assertFalse(info['sql_executed'])
        self.assertEqual(requested_schema('แสดงคอลัมน์ของตาราง orders'), ('orders',))
        self.assertIsNone(requested_schema('ยอดขายตามคอลัมน์ country เท่าไร'))
    def test_valid_diagnostic_aggregations_are_not_false_rejected(self):
        for case in json.loads((ROOT/'reports/aggregation-contract-audit.json').read_text(encoding='utf-8'))['cases']:
            with self.subTest(case=case['id']):
                q,sql=case['question'],case['sql']
                validate_sql(sql);validate_semantics(q,sql)
                validate_business_sql(q,sql);validate_metric_expression(q,sql)
    def test_multiple_dimensions_do_not_get_a_guessed_hard_column_count(self):
        for q in ('ยอดขายรวมแยกตามประเทศและเดือน','Show total sales by country and month'):
            self.assertNotIn('output_column_count',request_constraints(q))
    def test_explicit_projection_still_rejects_extra_columns(self):
        with self.assertRaises(ValueError):
            validate_metric_expression('สินค้า 5 อันดับ แสดงรหัสและค่า','SELECT product_id,description,SUM(line_amount) FROM sales_lines GROUP BY product_id,description')
    def test_unrequested_grouping_is_still_rejected(self):
        with self.assertRaises(ValueError):
            validate_semantics('ยอดขายรวมเท่าไร ตลอดช่วงข้อมูลทั้งหมด','SELECT country,SUM(order_amount) FROM orders GROUP BY country')
    def test_each_product_can_return_revenue_and_units_together(self):
        question = 'มีสินค้าอะไรบ้าง และยอดขายแต่ละอย่างเท่าไรและจำนวนเท่าไร'
        sql = ("SELECT product_id, description, SUM(line_amount) AS sales, SUM(quantity) AS units "
               "FROM sales_lines WHERE transaction_type = 'sale' "
               "GROUP BY product_id, description ORDER BY product_id")
        validate_sql(sql)
        validate_semantics(question, sql)
        validate_business_sql(question, sql)
        validate_metric_expression(question, sql)
        self.assertIn('product_sales_and_units', request_constraints(question))
    def test_wrong_source_period_and_writes_still_reject(self):
        for sql in ('DELETE FROM orders','SELECT * FROM secret_customers'):
            with self.assertRaises(ValueError):validate_sql(sql)
        with self.assertRaises(ValueError):
            validate_business_sql('Count completed invoices in January 2011','SELECT COUNT(*) FROM sales_lines')
        with self.assertRaises(ValueError):
            validate_business_sql('ยอดขายรวมเดือนมกราคม 2011','SELECT SUM(order_amount) FROM orders')
    def test_all_group_dimensions_are_used_for_uniqueness(self):
        for group in ("country,DATE_TRUNC('MONTH',order_ts)",'country,month','1,2'):
            sql="SELECT country,DATE_TRUNC('MONTH',order_ts) AS month,SUM(order_amount) FROM orders GROUP BY "+group
            valid={'columns':['country','month','sales'],'rows':[['UK','2011-01-01',10],['UK','2011-02-01',20]],'truncated':False}
            self.assertNotIn('duplicate_group_keys',result_violations('',valid,sql))
            invalid=dict(valid,rows=[['UK','2011-01-01',10],['UK','2011-01-01',20]])
            self.assertIn('duplicate_group_keys',result_violations('',invalid,sql))
    def test_missing_projected_group_key_does_not_create_false_duplicates(self):
        sql="SELECT country,SUM(order_amount) FROM orders GROUP BY country,DATE_TRUNC('MONTH',order_ts)"
        result={'columns':['country','sales'],'rows':[['UK',10],['UK',20]],'truncated':False}
        self.assertNotIn('duplicate_group_keys',result_violations('',result,sql))
    def test_explicit_product_id_sort_is_not_replaced_by_revenue_rank(self):
        q='แต่ละสินค้ามียอดขายเท่าไร เรียงรหัสสินค้า'
        good='SELECT product_id,SUM(line_amount) AS sales FROM sales_lines GROUP BY product_id ORDER BY product_id'
        validate_metric_expression(q,good)
        with self.assertRaises(ValueError):validate_metric_expression(q,good.replace('ORDER BY product_id','ORDER BY sales DESC'))
