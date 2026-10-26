import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from agent import answer
from dataset_info import is_dataset_discovery, overview

ROOT=Path(__file__).resolve().parents[1]
SCHEMA={'orders':'struct<invoice_id:string,order_amount:decimal(18,4)>',
        '_dataset_metadata':{'as_of_date':'2011-12-01','observed_min_timestamp':'2009-12-01 07:45:00','observed_max_timestamp':'2011-12-09 12:50:00'}}


class DatasetInfoTests(unittest.TestCase):
    def test_discovery_does_not_call_model_or_spark(self):
        for q in ('มีข้อมูลอะไรบ้าง','มีข้อมูลอะไร','What data is available?','What tables do you have?'):
            with self.subTest(q=q),patch('agent.generate',side_effect=AssertionError('No model')):
                r=answer(q,SCHEMA,lambda sql:self.fail('No SQL'),'fixture','unused',ROOT/'knowledge')
                self.assertEqual(r['status'],'information')
                self.assertEqual(r['model_calls'],0)
                self.assertEqual([row[0] for row in r['result']['rows']],['orders'])
                self.assertEqual(r['citations'],['schema.orders'])
                self.assertIn('2011-12-01',r['message'])
    def test_analytical_questions_are_not_discovery(self):
        for q in ('ยอดขายรวมเท่าไร','มีข้อมูลยอดขายเดือนตุลาคม 2011 เท่าไร','What data is available? Also count invoices in 2011','Count orders in October 2011'):
            self.assertFalse(is_dataset_discovery(q))
    def test_columns_and_missing_metadata_are_not_invented(self):
        r=overview(SCHEMA)
        self.assertEqual(r['result']['rows'][0][3],'invoice_id, order_amount')
        r=overview({})
        self.assertEqual(r['result']['rows'],[])
        self.assertNotIn('2011',r['message'])
    def test_thai_analytical_request_still_asks_for_period_in_thai(self):
        with patch('agent.generate',side_effect=AssertionError('No model')):
            r=answer('ยอดขายรวมเท่าไร',SCHEMA,lambda sql:self.fail('No SQL'),'fixture','unused',ROOT/'knowledge')
        self.assertEqual(r['status'],'clarification')
        self.assertIn('ช่วงเวลา',r['message'])
        self.assertNotIn('Which',r['message'])
