"""Chart data is derived only from validated query results, never generated code."""
import math
from decimal import Decimal
from typing import Any


def chart_data(answer: dict[str, Any]) -> dict[str, Any] | None:
    if answer.get('status') != 'executed' or not answer.get('result_contract'):
        return None
    result = answer['result']
    rows, columns = result['rows'], result['columns']
    if not rows or len(columns) < 2:
        return None
    numeric = [i for i in range(len(columns)) if all(
        len(row)==len(columns) and isinstance(row[i], (int,float,Decimal))
        and not isinstance(row[i],bool) and math.isfinite(float(row[i])) for row in rows)]
    if not numeric:
        return None
    return {'columns':columns, 'numeric_indices':numeric,
            'rows':[[float(value) if i in numeric else str(value)[:120]
                     for i,value in enumerate(row)] for row in rows[:100]],
            'truncated':bool(result.get('truncated')) or len(rows)>100}
