import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from question_scope import apply_time_selection,validate_time_selection
from semantic_contracts import requested_period
class WebTimeTests(unittest.TestCase):
    def test_all_data_is_visible_and_not_injected_without_selection(self):
        q='ยอดขายรวมเท่าไร'
        resolved,scope=apply_time_selection(q,{}, {'mode':'all'})
        self.assertIn('all available data',resolved)
        self.assertEqual(scope['source'],'web_selection')
        self.assertEqual(apply_time_selection(q,{},None),(q,None))
    def test_custom_dates_are_inclusive_with_half_open_execution(self):
        q,s=apply_time_selection('ยอดขายรวมเท่าไร',{}, {'mode':'custom','start':'2011-01-01','end':'2011-01-31'})
        self.assertEqual(requested_period(q),['2011-01-01','2011-02-01'])
        self.assertEqual(s['end'],'2011-01-31')
    def test_question_period_and_snapshot_override_selection(self):
        for q in ('ยอดขายเดือนมกราคม 2011','ยอดขายตลอดช่วงข้อมูลทั้งหมด','ลูกค้า high-value','คำสั่งซื้อเดือนนี้'):
            self.assertEqual(apply_time_selection(q,{}, {'mode':'custom','start':'2010-01-01','end':'2010-01-31'})[0],q)
    def test_invalid_ranges_and_extra_fields_are_rejected(self):
        for s in ({'mode':'custom','start':'2011-02-30','end':'2011-03-01'},{'mode':'custom','start':'2011-03-01','end':'2011-01-01'},{'mode':'all','sql':'SELECT 1'},{'mode':'unknown'}):
            with self.subTest(selection=s),self.assertRaises(ValueError):validate_time_selection(s)
