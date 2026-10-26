"""OPA is mandatory at the Spark tool boundary; transport/undefined errors deny."""
import json
import os
from urllib.request import Request, urlopen
from sqlglot import parse_one, exp
from sqlglot.optimizer.scope import traverse_scope


class PolicyUnavailable(ValueError):
    pass


def policy_facts(sql, attempt, stage='pre', violations=None):
    tree = parse_one(sql, read='spark')
    tables = sorted({source.name.lower() for scope in traverse_scope(tree)
                     for source in scope.sources.values() if isinstance(source, exp.Table)})
    return {'stage': stage, 'read_only': isinstance(tree, (exp.Select, exp.Union)),
            'guard_passed': True, 'tables': tables, 'row_cap': 200,
            'attempt': attempt, 'result_violations': violations or []}


def authorize(facts, endpoint=None):
    endpoint = endpoint or os.environ.get('OPA_URL', 'http://opa:8181')
    request = Request(endpoint.rstrip('/') + '/v1/data/analytics/decision',
                      data=json.dumps({'input': facts}).encode(),
                      headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=5) as response:
            decision = json.load(response).get('result')
        if (not isinstance(decision, dict) or not isinstance(decision.get('allow'), bool)
                or not isinstance(decision.get('reasons'), list)):
            raise ValueError('Undefined or malformed policy decision')
    except Exception as error:
        raise PolicyUnavailable('OPA unavailable or invalid decision; execution blocked') from error
    if decision['allow'] is not True:
        raise ValueError('OPA denied: ' + ', '.join(map(str, decision['reasons'])))
    return dict(decision, stage=facts['stage'], engine='OPA/Rego')
