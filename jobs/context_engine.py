"""Assemble auditable, lossless selected evidence and bounded repair state."""
import hashlib
import json


def compact_json(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':'))


def assemble_evidence(references, background='', strategy='managed', position='middle'):
    """Background is optional untrusted material, never selected metric evidence.

    Production uses managed and no background. Unfiltered is an evaluation control;
    both strategies retain ALL selected RAG evidence, including required policies.
    """
    if strategy not in ('managed','unfiltered') or position not in ('front','middle','end'):
        raise ValueError('Unknown context strategy or evidence position')
    unique={}
    original=[]
    for ref in references:
        ident,body=ref['id'],ref['text']
        if ident in unique and unique[ident]['text']!=body:
            raise ValueError('Conflicting evidence bodies for ID: '+ident)
        if ident not in unique:
            original.append(ref)
            unique[ident]={'id':ident,'text':body}
    selected=list(unique.values())
    # Canonical minimal facts support auditing. Preserve the existing model-facing
    # evidence representation: stripping metadata changed model behavior in v1.
    required=compact_json(selected)
    model_evidence=json.dumps(original,ensure_ascii=False)
    supplied_background=background if strategy=='unfiltered' else ''
    midpoint=len(supplied_background)//2
    before,after={'front':('',supplied_background),
                  'middle':(supplied_background[:midpoint],supplied_background[midpoint:]),
                  'end':(supplied_background,'')}[position]
    # JSON serialization prevents source text from closing our section boundaries.
    packet=(model_evidence if not supplied_background else
            '{"untrusted_background_before":'+compact_json(before)+
            ',"selected_rag_evidence":'+model_evidence+
            ',"untrusted_background_after":'+compact_json(after)+'}')
    trace={'strategy':strategy,'selected_ids':list(unique),
           'all_selected_evidence_retained':True,'selected_evidence_sha256':hashlib.sha256(required.encode()).hexdigest(),
           'packet_sha256':hashlib.sha256(packet.encode()).hexdigest(),
           'packet_utf8_bytes':len(packet.encode()),'background_input_characters':len(background),
           'background_supplied_characters':len(supplied_background),
           'background_omitted_characters':len(background)-len(supplied_background),
           'requested_evidence_position':position,
           'effective_evidence_position':position if supplied_background else 'selected_evidence_only',
           'duplicates_removed':len(references)-len(unique)}
    trace['wire_format']='legacy-evidence-json-preserved'
    return packet,trace


def repair_messages(original, proposal, error):
    """Keep original task/facts and latest SQL/error; never summarize business facts."""
    state={key:proposal[key] for key in ('sql','citations','grain') if key in proposal}
    # Preserve the first error line, not a Spark physical plan or model explanation.
    reason=str(error).splitlines()[0][:700]
    return list(original[:2])+[
        {'role':'assistant','content':compact_json(state)},
        {'role':'user','content':'Rejected: '+reason+'. Repair the SQL using the original question and evidence.'}]
