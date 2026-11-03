"""Small metadata-only tools. Model requests cannot access rows or execute code."""
from sql_guard import TABLES


def observe_tools(proposal, schema):
    plan = proposal.get('plan', [])
    if not isinstance(plan, list) or len(plan) > 8 or any(
            not isinstance(step, str) or len(step) > 200 for step in plan):
        raise ValueError('Plan must contain at most eight short action labels')
    requests = proposal.get('tools', [])
    if not isinstance(requests, list) or len(requests) > 4:
        raise ValueError('At most four metadata tools per attempt')
    observations = []
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError('Tool request must be an object')
        name = request.get('name')
        if name == 'list_tables' and set(request) == {'name'}:
            result = sorted(TABLES.intersection(schema))
        elif name == 'describe_table' and set(request) == {'name', 'table'}:
            table = request['table']
            if not isinstance(table, str) or table not in TABLES or table not in schema:
                raise ValueError('Unknown analytics table')
            result = schema.get('_table_metadata',{}).get(table, schema[table])
        else:
            raise ValueError('Unsupported metadata tool')
        observations.append({'tool': name, 'result': result})
    return observations
