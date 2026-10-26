"""Deterministic retrieval/evidence metrics. Qrels never enter agent prompts."""
import math


def percentile95(values):
    return sorted(values)[max(0,math.ceil(len(values)*0.95)-1)] if values else None


def retrieval_metrics(ranked_ids, relevant_ids, context_ids=None):
    relevant = set(relevant_ids)
    if not relevant:
        raise ValueError('Retrieval metrics require labeled relevant evidence')
    hits = [1 if ident in relevant else 0 for ident in ranked_ids]
    dcg = sum(hit/math.log2(i+2) for i,hit in enumerate(hits))
    ideal = sum(1/math.log2(i+2) for i in range(min(len(relevant),len(ranked_ids))))
    first = next((i+1 for i,hit in enumerate(hits) if hit),None)
    return {'recall_at_6':len(set(ranked_ids)&relevant)/len(relevant),
            'precision_at_6':sum(hits)/6,
            'mrr_at_6':1/first if first else 0,
            'ndcg_at_6':dcg/ideal if ideal else 0,
            'context_coverage':len(set(context_ids or ranked_ids)&relevant)/len(relevant)}
