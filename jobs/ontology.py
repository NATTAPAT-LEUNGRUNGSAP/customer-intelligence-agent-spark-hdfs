"""Small domain OWL graph, SHACL validation and evidence dependency resolution."""
import hashlib
import re
from functools import lru_cache
from pathlib import Path
from rdflib import Graph, Namespace, RDF
from rdflib.namespace import SKOS
from pyshacl import validate

CI = Namespace('urn:ci:')
ROOT = Path(__file__).resolve().parents[1] / 'ontology'


def validate_graph(graph, shapes):
    conforms, _, message = validate(graph, shacl_graph=shapes, inference='none')
    if not conforms:
        raise ValueError('Ontology SHACL validation failed: ' + str(message)[:1200])
    for metric in graph.subjects(RDF.type, CI.Metric):
        table = graph.value(metric, CI.sourceTable)
        if graph.value(metric, CI.hasGrain) != graph.value(table, CI.hasGrain):
            raise ValueError('Ontology source grain mismatch')


@lru_cache(maxsize=4)
def _load(signature):
    graph = Graph().parse(ROOT / 'customer-intelligence.ttl', format='turtle')
    shapes = Graph().parse(ROOT / 'shapes.ttl', format='turtle')
    validate_graph(graph, shapes)
    entries = []
    for metric in sorted(graph.subjects(RDF.type, CI.Metric), key=str):
        table = graph.value(metric, CI.sourceTable)
        entries.append({'concept': str(metric),
            'labels': [str(v) for p in (SKOS.prefLabel, SKOS.altLabel) for v in graph.objects(metric, p)],
            'table': str(graph.value(table, CI.sqlName)),
            'grain': str(graph.value(metric, CI.hasGrain)).removeprefix('urn:ci:'),
            'formula': str(graph.value(metric, CI.formula)),
            'evidence_ids': [str(graph.value(graph.value(node, CI.definedBy), CI.evidenceId))
                             for node in (metric, table)]})
    return entries, hashlib.sha256(b''.join((ROOT / n).read_bytes() for n in
                         ('customer-intelligence.ttl', 'shapes.ttl'))).hexdigest()


def resolve(question):
    signature = tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size)
                      for p in sorted(ROOT.glob('*.ttl')))
    entries, digest = _load(signature)
    def matches(label):
        pattern = re.escape(label.lower())
        if re.fullmatch(r'[a-z0-9 -]+', label.lower()):
            pattern = r'(?<![a-z])' + pattern + r'(?![a-z])'
        return re.search(pattern, question.lower()) is not None
    matched = [e for e in entries if any(matches(label) for label in e['labels'])]
    return {'status': 'validated', 'format': 'RDF/OWL + SHACL', 'sha256': digest,
            'domain_metrics': len(entries), 'matches': matched}
