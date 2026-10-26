"""Cached BM25 retrieval with bilingual concepts and stable evidence sections."""
import hashlib
import math
import re
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path

CONCEPTS = {
 'sales': r'sales|revenue|ยอดขาย', 'orders': r'orders?|invoices?|คำสั่งซื้อ|ใบสั่งซื้อ|กี่ใบ',
 'customers': r'customers?|ลูกค้า', 'repeat': r'repeat|at least two|two or more|ซื้อซ้ำ',
 'aov': r'\baov\b|average order value|average basket|เฉลี่ยต่อคำสั่งซื้อ',
 'anonymous': r'anonymous|unidentified|missing.?id|ไม่ระบุตัวตน|ไม่ทราบรหัส',
 'high_value': r'high[ -]value|มูลค่าสูง', 'champions': r'champions?|แชมเปี้ยน',
 'inactive': r'inactive|ไม่เคลื่อนไหว', 'segment': r'segments?|\brfm\b|กลุ่มลูกค้า',
 'products': r'products?|sku|สินค้า', 'returns': r'\breturns\b|\breturned\b|\breturn (?:product |sale )?lines\b|คืนสินค้า',
 'cancellation': r'cancellations?|ยกเลิก', 'snapshot': r'snapshot|as.of|ณ วันที่|ภาพรวม ณ',
 'availability': r'profit|margin|cost|uplift|campaign|กำไร|ต้นทุน|แคมเปญ',
 'period': r'period|time range|ช่วงเวลา|january|february|march|april|may|june|july|august|september|october|november|december|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม|\b(?:19|20)\d{2}\b',
 'joins': r'join|fanout|repeated.invoice|ซ้ำยอด',
}
STOP = set('a an the in at of to for from what how were was is are be with and or by '
           'return show give many there our all that this then as on per'.split())
POLICIES = ('policy.period', 'policy.availability', 'policy.snapshot')
TOPICS = {
 'metric.sales':('sales',), 'metric.orders':('orders','anonymous'),
 'metric.aov':('aov',), 'metric.customers':('customers',),
 'metric.repeat_rate':('repeat',), 'metric.high_value':('high_value',),
 'segment.champions':('champions',), 'segment.inactive':('inactive',),
 'segment.distribution':('segment',),
 'schema.orders':('orders','aov','sales','repeat','anonymous','customers'),
 'schema.sales_lines':('products','cancellation','returns'),
 'schema.customer_summary':('snapshot','segment','champions','inactive','high_value'),
 'schema.joins':('joins',), 'syntax.time':('period',),
 'syntax.ranking':(), 'syntax.aggregation':('repeat',),
 'policy.period':('period',), 'policy.availability':('availability',),
 'policy.snapshot':('snapshot',),
}


def tokens(text):
    text = text.lower()
    words = [w for w in re.findall(r'[a-z_]+|[\u0e00-\u0e7f]+', text) if w not in STOP]
    grams = [w[i:i+3] for w in words if re.search(r'[\u0e00-\u0e7f]', w)
             for i in range(max(0, len(w)-2))]
    concepts = ['concept_'+name for name, pattern in CONCEPTS.items() if re.search(pattern, text)]
    return words + grams + concepts*3


def load_chunks(directory):
    chunks = []
    for path in sorted(Path(directory).glob('*.md')):
        content = path.read_text(encoding='utf-8')
        for match in re.finditer(r'^## ([a-z][a-z0-9_.]+)\s*\n(.*?)(?=^## |\Z)', content, re.M|re.S):
            ident, body = match.group(1), match.group(2).strip()
            chunks.append({'id': ident, 'source': path.name, 'text': body,
                           'sha256': hashlib.sha256(body.encode()).hexdigest()})
    if not chunks or len({c['id'] for c in chunks}) != len(chunks):
        raise ValueError('Knowledge must contain unique stable ## section IDs')
    return chunks


@lru_cache(maxsize=8)
def _index(directory, signatures):
    chunks = load_chunks(directory)
    counts = [Counter(tokens(c['id']+' '+c['text'])) for c in chunks]
    df = Counter(term for count in counts for term in count)
    average = sum(sum(c.values()) for c in counts)/len(counts)
    return chunks, counts, df, average


def index(directory):
    root = Path(directory).resolve()
    signatures = tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size)
                       for p in sorted(root.glob('*.md')))
    return _index(str(root), signatures)


def retrieve(question, directory, k=6):
    if not 1 <= k <= 12:
        raise ValueError('Retrieval k must be 1..12')
    chunks, counts, df, average = index(directory)
    ranked = []
    query = Counter(tokens(question))
    for chunk, count in zip(chunks, counts):
        score, length = 0.0, sum(count.values())
        for term, qf in query.items():
            tf = count[term]
            if tf:
                idf = math.log(1+(len(chunks)-df[term]+0.5)/(df[term]+0.5))
                score += min(qf,3)*idf*tf*2.2/(tf+1.2*(0.25+0.75*length/average))
        # Primary-topic field prevents negative examples from outranking the rule
        # itself (e.g. a different rule mentioning "not invoices"). No SQL routing.
        boost = 10 if chunk['id'].startswith(('metric.','segment.')) else 4
        score += boost*sum('concept_'+topic in query for topic in TOPICS.get(chunk['id'],()))
        if score > 0:
            ranked.append(dict(chunk,score=score))
    ranked = sorted(ranked,key=lambda c:(-c['score'],c['id']))
    if not ranked:
        return []
    by_id = {c['id']:dict(c,score=0.0) for c in chunks}
    by_id.update({c['id']:c for c in ranked})
    selected = []
    def add(ident,selection):
        if ident in by_id and ident not in {c['id'] for c in selected} and len(selected)<k:
            selected.append(dict(by_id[ident],selection=selection))
    def dependency(ident):
        if ident.startswith('segment.') or ident=='metric.high_value':
            add('schema.customer_summary','schema_dependency')
        elif ident.startswith('metric.'):
            add('schema.orders','schema_dependency')
            add('policy.period','policy_dependency')
    # Retrieve the rule and its table definition together, rather than hoping
    # general schema wording independently ranks above six lexical distractors.
    # Resolve explicit metric language before generic mentions of "customers".
    # This chooses evidence, never SQL or a query template.
    primary=None
    if not any('concept_'+topic in query for topic in ('snapshot','segment','champions','inactive','high_value')):
        for topic,ident in [('repeat','metric.repeat_rate'),('aov','metric.aov'),('sales','metric.sales'),('orders','metric.orders')]:
            if 'concept_'+topic in query:
                primary=ident
                break
    if primary:
        add(primary,'explicit_metric')
    add(ranked[0]['id'],'lexical_head')
    if any('concept_'+topic in query for topic in ('products','cancellation','returns')):
        add('schema.sales_lines','grain_dependency')
    if any('concept_'+topic in query for topic in ('snapshot','segment','champions','inactive','high_value')):
        add('schema.customer_summary','grain_dependency')
        add('policy.snapshot','policy_dependency')
    facts=[c['id'] for c in ranked if c['id'].startswith(('metric.','segment.'))]
    if primary:
        facts=[primary]+[ident for ident in facts if ident!=primary]
    if facts:
        add(facts[0],'primary_fact')
        dependency(facts[0])
    if re.search(r'\btop\b|highest|greatest|most.*first|สูงสุด',question.lower()):
        add('syntax.ranking','syntax_dependency')
    if 'concept_period' in query:
        add('syntax.time','syntax_dependency')
    if len(facts)>1:
        add(facts[1],'secondary_fact')
        dependency(facts[1])
    for chunk in ranked:
        add(chunk['id'],'lexical')
    return selected


def retrieve_context(question, directory, k=6):
    started = time.perf_counter()
    chunks = index(directory)[0]
    by_id = {c['id']:c for c in chunks}
    if not all(ident in by_id for ident in POLICIES):
        raise ValueError('Required RAG policy documents are missing')
    ranked = retrieve(question,directory,k)
    selected = list(ranked)
    for ident in POLICIES:
        if ident not in {c['id'] for c in selected}:
            selected.append(dict(by_id[ident],score=None,selection='mandatory_policy'))
    corpus_hash = hashlib.sha256(''.join(c['id']+c['sha256'] for c in chunks).encode()).hexdigest()
    return selected, {'method':'BM25+bilingual-topic+metric-schema-syntax-expansion-v2.4','ranked_ids':[c['id'] for c in ranked],
        'context_ids':[c['id'] for c in selected], 'corpus_sha256':corpus_hash,
        'corpus_chunks':len(chunks),'context_characters':sum(len(c['text']) for c in selected),
        'elapsed_ms':(time.perf_counter()-started)*1000}
