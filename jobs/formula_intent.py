"""Read a requested known formula from RAG; never execute a free-form expression."""
import re


def requested_formula(question, chunks):
    match=re.fullmatch(r'(?:ขอสูตร(.+?)\s*ไม่ต้องรัน SQL|Explain the formula for (.+?); do not execute SQL\.)',question.strip(),re.I)
    if not match:return None
    term=(match[1] or match[2]).strip().lower()
    for chunk in chunks:
        if not chunk['id'].startswith('formula.'):continue
        names=re.search(r'^Name: (.+)$',chunk['text'],re.M)
        if names and term in [n.strip().lower() for n in names[1].split(' / ')]:return chunk['id']
    return 'unknown'


def formula_response(ident, chunk):
    fields=dict(re.findall(r'^(Name|Formula|SQL expression|Source table|Meaning): (.+)$',chunk['text'],re.M))
    if len(fields)!=5:raise ValueError('Incomplete formula evidence')
    return {'status':'information','intent':'formula','formula_id':ident.removeprefix('formula.'),
            'message':'สูตรจากนิยามที่ตรวจสอบได้ ยังไม่ได้คำนวณผลหรือรัน SQL\n'+fields['Meaning'],
            'result':{'columns':['สูตร','นิยาม','Spark SQL expression','ตารางต้นทาง'],
                      'rows':[[fields['Name'],fields['Formula'],fields['SQL expression'],fields['Source table']]],'truncated':False},
            'citations':[ident,'schema.'+fields['Source table']],
            'model_calls':0,'sql_executed':False,'attempts':[]}
