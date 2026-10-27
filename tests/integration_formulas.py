"""Execute RAG formula expressions on controlled Spark fixtures, not a mock LLM."""
import json
import sys
from datetime import datetime,date
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'jobs'))
from retrieval import load_chunks
from query_runtime import run_query
from sql_guard import validate_sql
from evaluate import same_result


def main():
    from pyspark.sql import SparkSession
    spark=SparkSession.builder.appName('formula-numeric-contracts').config('spark.sql.session.timeZone','UTC').getOrCreate()
    spark.sparkContext.setLogLevel('WARN')
    report={'status':'running','method':'actual Spark SQL on controlled numerical fixtures; no model calls','cases':[]}
    path=Path('/app/reports/bilingual-formula-integration.json')
    def save():path.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    save()
    try:
        rows=[('1','A',datetime(2011,1,1),Decimal(10),2,'X'),
              ('2','A',datetime(2011,1,2),Decimal(30),4,'X'),
              ('3','B',datetime(2011,2,1),Decimal(20),6,'Y'),
              ('4',None,datetime(2011,2,2),Decimal(40),8,'X')]
        spark.createDataFrame(rows,'invoice_id string,customer_id string,order_ts timestamp,order_amount decimal(18,4),total_units long,country string').createOrReplaceTempView('orders')
        spark.createDataFrame([('sale',2,Decimal(10)),('sale',3,Decimal(30)),('cancellation',-1,Decimal(-5)),('return',-1,Decimal(-10))],
                              'transaction_type string,quantity long,line_amount decimal(18,4)').createOrReplaceTempView('sales_lines')
        spark.createDataFrame([('A',True,date(2011,12,1)),('B',False,date(2011,12,1))],
                              'customer_id string,is_high_value boolean,as_of_date date').createOrReplaceTempView('customer_summary')
        monthly="SELECT DATE_TRUNC('MONTH',order_ts) AS month,SUM(order_amount) AS sales FROM orders GROUP BY DATE_TRUNC('MONTH',order_ts)"
        frequency='SELECT customer_id,COUNT(*) AS invoice_frequency FROM orders WHERE customer_id IS NOT NULL GROUP BY customer_id'
        import re
        formulas={c['id'].removeprefix('formula.'):re.search(r'^SQL expression: (.+)$',c['text'],re.M)[1] for c in load_chunks('/app/knowledge') if c['id'].startswith('formula.')}
        expected={'aov':[[25]],'repeat_rate':[[0.5]],'anonymous_share':[[0.25]],'units_per_order':[[5]],
                  'product_revenue':[[40]],'mom_growth':[[None],[0.5]],'country_share':[[0.8],[0.2]],
                  'cumulative_sales':[[40],[100]],'moving_average':[[40],[50]],'median_order':[[20]],
                  'high_value_share':[[0.5]],'cancellation_share':[[0.25]]}
        def check(name,sql,wanted):
            actual=run_query(spark,validate_sql(sql))
            correct=same_result(actual,{'rows':wanted,'truncated':False},True)
            report['cases'].append({'id':name,'sql':sql,'expected_rows':wanted,'actual':actual,'correct':correct});save()
            print(name,correct,flush=True)
        for key,expression in formulas.items():
            if key in ('mom_growth','cumulative_sales','moving_average'):
                sql=f'WITH m AS ({monthly}) SELECT {expression} AS value FROM m ORDER BY month'
            elif key=='country_share':
                sql=f'WITH c AS (SELECT country,SUM(order_amount) AS sales FROM orders GROUP BY country) SELECT {expression} AS value FROM c ORDER BY country'
            elif key=='repeat_rate':sql=f'WITH f AS ({frequency}) SELECT {expression} AS value FROM f'
            else:
                source='sales_lines' if key in ('product_revenue','cancellation_share') else 'customer_summary' if key=='high_value_share' else 'orders'
                sql=f'SELECT {expression} AS value FROM {source}'+(" WHERE transaction_type='sale'" if key=='product_revenue' else " WHERE as_of_date=DATE '2011-12-01'" if key=='high_value_share' else '')
            check(key,sql,expected[key])
        check('empty_aov','SELECT '+formulas['aov']+' FROM orders WHERE 1=0',[[None]])
        check('empty_repeat','WITH f AS ('+frequency.replace('customer_id IS NOT NULL','customer_id IS NOT NULL AND 1=0')+') SELECT '+formulas['repeat_rate']+' FROM f',[[None]])
        zero_monthly=monthly.replace('SUM(order_amount)',"SUM(CASE WHEN MONTH(order_ts)=1 THEN 0 ELSE order_amount END)")
        check('zero_growth_base','WITH m AS ('+zero_monthly+') SELECT '+formulas['mom_growth']+' FROM m ORDER BY month',[[None],[None]])
        negative_monthly=monthly.replace('SUM(order_amount)',"SUM(CASE WHEN MONTH(order_ts)=1 THEN order_amount*2 ELSE order_amount/3 END)")
        check('negative_growth','WITH m AS ('+negative_monthly+') SELECT '+formulas['mom_growth']+' FROM m ORDER BY month',[[None],[-0.75]])
        report.update(status='passed' if all(c['correct'] for c in report['cases']) else 'failed',correct=sum(c['correct'] for c in report['cases']),total=len(report['cases']))
        save()
        if report['status']!='passed':raise AssertionError('Formula numerical examples failed')
    except Exception as error:
        report.update(status='failed',error=str(error));save();raise
    finally:spark.stop()


if __name__=='__main__':main()
