"""Summarize one frozen RAG holdout run. No with/without-RAG comparison."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evaluation',required=True)
    parser.add_argument('--retrieval',required=True)
    parser.add_argument('--freeze',default='reports/freeze-rag-v2.1.json')
    args=parser.parse_args()
    evaluation,retrieval,frozen=read(args.evaluation),read(args.retrieval),read(args.freeze)
    assert evaluation['status']==retrieval['status']=='completed'
    assert evaluation['split']==retrieval['split']=='holdout'
    assert len(evaluation['cases'])==len(retrieval['cases'])==20
    for name,digest in frozen['provenance']['files_sha256'].items():
        assert evaluation['provenance']['files_sha256'].get(name)==digest,'Evaluation freeze mismatch: '+name
        assert retrieval['provenance']['files_sha256'].get(name)==digest,'Retrieval freeze mismatch: '+name
    assert frozen['provenance']['model']['digest']==evaluation['provenance']['model']['digest']
    assert frozen['build_run_id']==evaluation['build_run_id'],'Build run mismatch'
    summary={'status':'completed','version':evaluation.get('version','rag-required-v2'),'rag_required':True,
             'quality_passed':evaluation['quality_passed'] and retrieval['quality_passed'],
             'source_reports':{'evaluation':args.evaluation,'retrieval':args.retrieval,'freeze':args.freeze},
             'end_to_end':evaluation['summary'],'retrieval':retrieval['summary'],
             'checks':{'end_to_end':evaluation['quality_checks'],'retrieval':retrieval['quality_checks']},
             'written_at_utc':datetime.now(timezone.utc).isoformat()}
    development=[read(Path('reports')/name) for name in frozen.get('development_reports',[])]
    summary['development']=[{'split':r['split'],'summary':r['summary']} for r in development]
    if frozen.get('prior_failed_holdout'):
        prior=read(Path('reports')/frozen['prior_failed_holdout'])
        summary['prior_failed_attempt']={'report':frozen['prior_failed_holdout'],
            'quality_passed':prior['quality_passed'],'recall_at_6':prior['retrieval']['recall_at_6']}
    wall_path=Path('reports/rag-v2.1-ask-wallclock.json')
    wall=read(wall_path) if wall_path.exists() else None
    if wall:
        assert wall['exit_code']==0,'User CLI demo did not succeed'
        summary['single_cli_demo']=wall
    Path('reports/rag-v2-quality-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    e,r=evaluation['summary'],retrieval['summary']
    lines=['# รายงานคุณภาพ RAG — '+summary['version'],'',
        'RAG เป็นส่วนบังคับของระบบ ไม่ประเมินเปรียบเทียบกับการปิด RAG',
        'เกณฑ์ผ่านประกาศก่อนทดสอบใน evaluation/quality_gates_v2.json','',
        '**ผลรวม: '+('ผ่านเกณฑ์ที่กำหนดของโครงการ' if summary['quality_passed'] else 'ยังมีเกณฑ์ที่ไม่ผ่าน')+'**','',
        '## ผลวัดชุดใหม่ 20 ข้อ','',
        '| ตัววัด | ผลจริง | เกณฑ์ |','|---|---:|---:|',
        f'| Retrieval Recall@6 | {r["recall_at_6"]:.2%} | >=95% |',
        f'| MRR@6 | {r["mrr_at_6"]:.4f} | >=0.85 |',
        f'| nDCG@6 | {r["ndcg_at_6"]:.4f} | >=0.80 |',
        f'| Retrieval p95 | {r["latency_p95_ms"]:.2f} ms | <=50 ms |',
        f'| Supplied context coverage | {r["context_coverage"]:.2%} | รายงานแยกจาก ranked retrieval |',
        f'| ผลคำตอบตรง gold Spark | {e["correct"]}/{e["total"]} ({e["accuracy"]:.0%}) | >=90% |',
        f'| Clarification correctness | {e["clarification_accuracy"]:.0%} | 100% |',
        f'| Citation IDs อยู่ใน context จริง | {e["citation_validity"]:.0%} | 100% |',
        f'| มี citation ตรงหลักฐานที่ติดป้าย | {e["cited_relevant_evidence_rate"]:.0%} | >=95% |',
        f'| Warm end-to-end p95 | {e["latency_p95_seconds"]:.2f} s | <=20 s |','',
        f'Model warm-up/load แยกต่างหาก: {evaluation.get("model_warmup_seconds",0):.2f} วินาที',
        f'Model calls รวม: {e["model_calls"]}; เวลาเฉลี่ยต่อคำถาม {e["latency_mean_seconds"]:.2f} วินาที','',
        'p95 ต่อคำถามไม่นับการเปิด Spark application/ลงทะเบียน views; เวลา CLI เต็มจะสูงกว่า','',
        '## วิธีและหลักฐาน','',
        '- ค้น BM25 + bilingual concepts/Thai n-grams จากนิยามแบบแยกประเด็น พร้อม cached index',
        '- ranked top 6 และ policy context แยกกัน; rank metrics ไม่นับ policy ที่บังคับแนบเพิ่ม',
        '- qrels เป็น evidence IDs ที่กำหนดไว้ล่วงหน้า Gold SQL/labels ไม่ส่งให้ Agent',
        '- Agent สร้าง SQL เอง พร้อม citations และตรวจความสอดคล้องกับหลักฐานก่อนรัน',
        '- ตรวจ citations ที่ไม่มีจริง ปฏิเสธ SQL อันตราย และจำกัดแถว/เวลา',
        '- ผล SQL เทียบกับ gold ที่รันจริงใน Spark บน HDFS ไม่ใช่คะแนนจากการรัน SQL สำเร็จ',
        '- freeze fingerprints ของ code/knowledge/config/model ตรงทั้งรายงาน retrieval และ end-to-end',
        '- ชุด test เดิมเป็น regression แล้ว ผลเปรียบเทียบเก่าอยู่ใน reports/archive/v1 ไม่ใช้รับรองรุ่นนี้','',
        '## ข้อผิดพลาดที่ยังพบ','']
    failed=[c for c in evaluation['cases'] if not c['correct']]
    if not failed:
        lines.append('ไม่พบคำตอบผิดตามเกณฑ์อัตโนมัติในชุดใหม่นี้')
    for case in failed:
        lines += [f'### {case["id"]}',case['question'],'',
                  'สถานะ: '+case['result']['status'],'',
                  'SQL: '+case['result'].get('sql','ไม่มี'),
                  'ข้อความ: '+case['result'].get('message',case['result'].get('error','')),'']
        if case['id']=='fresh08':
            lines.append('สาเหตุ: ไม่กรอง customer_id IS NOT NULL ทำให้กลุ่มลูกค้าไม่ระบุตัวตนติดอันดับ ทั้งที่ถาม identified customers')
    missing=[c for c in retrieval['cases'] if c['metrics']['recall_at_6']<1]
    lines += ['',f'มี retrieval cases ที่ได้หลักฐานไม่ครบ top 6: {len(missing)} ข้อ']
    for case in missing:
        lost=set(case['relevant_ids'])-set(case['trace']['ranked_ids'])
        lines.append('- '+case['id']+': ขาด '+', '.join(sorted(lost)))
    lines += ['', '## ประวัติและผล regression ที่ยังต้องเปิดเผย','',
        'ชุดใหม่รอบแรกไม่ผ่าน Recall@6 (90.83% เทียบเกณฑ์ 95%) แม้คำตอบถูก 19/20',
        'ผลเดิมไม่ถูกลบ: reports/rag-v2-first-holdout-report.md และ summary JSON',
        'หลังแก้ retrieval ใช้ชุดนั้นเป็น regression-v2; ชุดสุดท้ายครั้งนี้เป็น rag_holdout_v3.json','']
    for report in development:
        score=report['summary']
        lines.append(f'- {report["split"]}: {score["correct"]}/{score["total"]}; p95 {score["latency_p95_seconds"]:.2f} s')
        for case in report['cases']:
            if not case['correct']:
                lines.append('  - ข้อผิดพลาดที่ยังมีใน regression: '+case['id']+' — '+case['question'])
    lines += ['', '## ข้อจำกัด','',
        'คะแนนนี้เป็นผลชุดคำถามขนาดเล็กที่ผู้พัฒนากำหนด ไม่ใช่การรับรองโดยผู้ประเมินภายนอก',
        'Citation validity/relevance ไม่ได้พิสูจน์ entailment ของข้อความทุกประโยค',
        'ชุดคำถามใหม่มีทั้งรูปแบบใกล้เคียงงานเดิมและเงื่อนไขผสมใหม่ จึงไม่ใช่ตัวแทนทุกโจทย์ในโลกจริง',
        'ใช้ข้อมูล UCI ประวัติศาสตร์ 2009–2011 บนเครื่องเดียว ไม่มี HDFS authentication',
        'Spark cancellation เป็น best effort และยังต้องตรวจคำตอบสำคัญก่อนใช้ตัดสินใจ','',
        '## ทำซ้ำ','',
        'อ่าน README.md และ evaluation/README.md รัน retrieval และ -Split holdout หลัง freeze',
        'build run: '+evaluation['build_run_id'],
        'รายงานดิบ: '+args.evaluation+' / '+args.retrieval,
        'freeze: '+args.freeze,
        'สรุป machine-readable: reports/rag-v2-quality-summary.json','']
    if wall:
        lines += ['## เวลา CLI จริงหนึ่งตัวอย่าง','',
                  f'ask.ps1 รวมเปิด/ปิด Spark application: {wall["full_cli_wall_seconds"]:.2f} วินาที',
                  'เป็นหนึ่งตัวอย่างขณะโมเดลอุ่นอยู่ ไม่ใช่ p95 และไม่นำไปแทน warm query benchmark','']
    Path('reports/FINAL_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__':
    main()
