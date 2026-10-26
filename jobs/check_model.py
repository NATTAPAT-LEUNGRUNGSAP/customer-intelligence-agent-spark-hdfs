"""Real model generation smoke; never presented as Spark execution success."""
import argparse
import json
import time
from pathlib import Path
from agent import generate
from sql_guard import validate_sql


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--endpoint', default='http://localhost:11434')
    parser.add_argument('--model', default='qwen3.5:9b')
    args = parser.parse_args()
    started = time.monotonic()
    proposed = generate([
        {'role':'system','content':'Generate Spark SQL. Return JSON with sql only. Available view orders has country STRING, order_amount DECIMAL, order_ts TIMESTAMP. Sales is sum(order_amount). Use inclusive start/exclusive end. Do not use templates.'},
        {'role':'user','content':'Return total sales in GBP for October 2011.'}],
        args.model, args.endpoint, timeout=180)
    guarded = validate_sql(proposed['sql'])
    result = {'status':'generated_and_validated','model':args.model,
              'sql':proposed['sql'], 'guarded_sql':guarded,
              'elapsed_seconds':time.monotonic()-started,
              'spark_executed':False}
    Path('reports/model-smoke.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
