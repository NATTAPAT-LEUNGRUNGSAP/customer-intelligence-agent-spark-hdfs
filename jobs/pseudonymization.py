"""Opt-in export boundary; never modifies source IDs, joins or stored tables."""
import hashlib
import hmac


def pseudonymize_result(result, key):
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError('Pseudonym key must contain at least 32 bytes')
    columns = result['columns']
    indices = [i for i, name in enumerate(columns) if name.lower() == 'customer_id']
    rows = []
    for source in result['rows']:
        row = list(source)
        for i in indices:
            if row[i] is not None:
                row[i] = 'customer_' + hmac.new(key, b'customer_id\0' + str(row[i]).encode(),
                                               hashlib.sha256).hexdigest()
        rows.append(row)
    return dict(result, rows=rows)
