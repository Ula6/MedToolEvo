"""Real prose, unedited; predefined literal queries and offline span checks."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'code'))
from anchor_oracle import oracle


def main():
    data=json.loads((HERE.parent/'DocHopQA/DocHopQA_Dataset.json').read_text(encoding='utf-8'))
    def source(tid):
        t=next(t for t in data if t['id']==tid)
        c=next(c for c in t['context_list'] if c['type']=='text' and c['section'].lower() in ['results','3. results','result'])
        return {'task_id':tid,'source_id':c['pmc_id'],'section':c['section'],'text':c['content'],'original_question':t['question']}
    a,b=source(9152),source(9532)
    snippets=['studies','vitamin D','double\u2010blind','hypertension','ACEI/ARB medication','white European','__absent_literal_probe__']
    queries=[{'query_id':'q'+str(i+1),'text':s} for i,s in enumerate(snippets)]
    payload={'sources':[{'source_id':a['source_id'],'text':a['text']}],'queries':queries}
    expected=oracle(payload)
    assert [q['query_id'] for q in expected['queries'] if not q['matches']]==['q7']
    controls=[]
    for i,(text,q) in enumerate([(a['text'][:80],a['text'].split()[0]),(a['text'][-150:],'white European'),(a['text'][:80],'__absent_literal_probe__')]):
        assert text in a['text']
        controls.append({'construction':{'source_id':a['source_id'],'method':'Unedited contiguous original source excerpt; literal query only.'},
                         'payload':{'sources':[{'source_id':a['source_id'],'text':text}],'queries':[{'query_id':'control'+str(i),'text':q}]}})
    reuse={'sources':[{'source_id':b['source_id'],'text':b['text']}],
           'queries':[{'query_id':'new1','text':'studies'},{'query_id':'new2','text':'JOINS'},{'query_id':'new3','text':'__absent_literal_probe__'}]}
    case={'source_id':a['source_id'],'task_id':a['task_id'],'original_question':a['original_question'],
          'url':'https://pmc.ncbi.nlm.nih.gov/articles/'+a['source_id']+'/',
          'source_text':a['text'],'payload':payload,'source_sha256':hashlib.sha256(a['text'].encode()).hexdigest(),
          'construction':'Unmodified DocHopQA Results content; researcher-defined character-span task, not original medical QA.'}
    task={'id':'derived-unicode-source-anchors-20261109',
          'question':'Find every original-source occurrence of each literal query, with exact Unicode character start/end offsets and verbatim quotes under the fixed normalization rule. Preserve source identity and reject the absent probe. This verifies evidence anchoring, not whether the quoted text supports a medical conclusion.',
          'fixed_source_queue':[case],'controls':controls,'reuse_payload':reuse,
          'human_intervention':'Source selection, literal snippets, normalization/I/O/oracle/controls/reuse preset before first baseline. No invented medical assertions, source edits, baseline edits or hand-written candidate code.',
          'known_previous_development_capabilities':{'quote_locator':'Returns only first resolved quote per claim; no all-occurrence character-offset index or NFKC map.',
                                                   'weighted_statistical_summaries':'Numerical summaries; not applicable to text spans.'},
          'reuse_source':{'task_id':b['task_id'],'source_id':b['source_id'],'source_sha256':hashlib.sha256(b['text'].encode()).hexdigest()}}
    d=HERE/'data';d.mkdir(exist_ok=True)
    (d/'task.json').write_text(json.dumps(task,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'pass':True,'source_id':a['source_id'],'source_characters':len(a['text']),'source_sha256':case['source_sha256'],
             'queries':len(queries),'match_counts':[len(q['matches']) for q in expected['queries']],
             'unsupported_queries':expected['unsupported_query_ids'],'exact_dataset_content':True,'code_candidate_written':False}
    (d/'offline_preflight.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary))


if __name__=='__main__':main()
