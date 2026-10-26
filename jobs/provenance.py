"""Small reproducibility record; excludes datasets, reports and credentials."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


def fingerprint(root='/app', endpoint=None, model=None):
    root = Path(root)
    files = {}
    for directory, pattern in [('jobs','*.py'), ('knowledge','*.md'), ('sql','*.sql'),
                               ('evaluation','*.json'), ('infra/spark','*'),
                               ('infra/hadoop/config','*'),('web','*'),('scripts','*.ps1')]:
        for path in sorted((root/directory).glob(pattern)):
            if path.is_file():
                files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name in ('compose.yaml','compose.web.yaml','requirements-agent.txt'):
        path = root/name
        if path.is_file():
            files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {'files_sha256':files}
    if endpoint and model:
        with urlopen(endpoint.rstrip('/')+'/api/tags', timeout=10) as response:
            tags = json.load(response)
        matches = [m for m in tags.get('models',[]) if m['name']==model]
        if not matches:
            raise ValueError('Requested local model is not installed: '+model)
        result['model'] = matches[0]
    return result
