"""CPU-only independent Unicode/original-span and interface preflight."""
import json
from pathlib import Path
import sys
from schema_support import Draft202012Validator
from anchor_protocol import INPUT_SCHEMA,OUTPUT_SCHEMA
from anchor_oracle import oracle,normalize,evaluate


def main():
    def payload(text,query):return {'sources':[{'source_id':'S','text':text}],'queries':[{'query_id':'Q','text':query}]}
    assert oracle(payload('aaa','aa'))['queries'][0]['matches']==[
        {'source_id':'S','start':0,'end':2,'quote':'aa'},{'source_id':'S','start':1,'end':3,'quote':'aa'}]
    assert oracle(payload('\u00df','ss'))['queries'][0]['matches']==[{'source_id':'S','start':0,'end':1,'quote':'\u00df'}]
    assert not oracle(payload('\u00df','s'))['queries'][0]['matches']
    assert oracle(payload('X\uff21\t \u00a0Bz','a b'))['queries'][0]['matches']==[{'source_id':'S','start':1,'end':6,'quote':'\uff21\t \u00a0B'}]
    assert oracle(payload('D\u2010blind','D-blind'))['unsupported_query_ids']==['Q']
    # Exhaustive independent tiny-string substring oracle, including expansion boundaries.
    for original in ['aAa','\u00dfXss','\uff21  B','e\u0301','\u00b5m','x\t\ny']:
        for query in ['a','ss','s','a b','\u00e9','\u03bcm','x y']:
            expected=[]
            for a in range(len(original)):
                for b in range(a+1,len(original)+1):
                    if normalize(original[a:b])[0]==normalize(query)[0]:expected.append((a,b))
            actual=[(m['start'],m['end']) for m in oracle(payload(original,query))['queries'][0]['matches']]
            assert actual==sorted(expected),(original,query,actual,expected)
    bad=[{'sources':True,'queries':[]},payload('a',' '),{'sources':[{'source_id':'S','text':3}],'queries':[]},
         {'sources':[{'source_id':'S','text':'a'},{'source_id':'S','text':'b'}],'queries':[]}]
    for p in bad:
        try:oracle(p)
        except ValueError:pass
        else:raise AssertionError('Invalid input accepted')
    d=Path(sys.argv[1]);t=json.loads((d/'task.json').read_text(encoding='utf-8'))
    for p in [t['fixed_source_queue'][0]['payload'],t['reuse_payload']]+[c['payload'] for c in t['controls']]:
        Draft202012Validator(INPUT_SCHEMA).validate(p);e=oracle(p);Draft202012Validator(OUTPUT_SCHEMA).validate(e);assert evaluate(e,e)['pass']
        texts={s['source_id']:s['text'] for s in p['sources']}
        for q in e['queries']:
            for m in q['matches']:assert texts[m['source_id']][m['start']:m['end']]==m['quote']
    print(json.dumps({'pass':True,'fixed_unicode_checks':5,'exhaustive_tiny_string_queries':42,'invalid_checks':4,
                      'real_payload_checks':5,'models_called':False,'scope':'Offline oracle/schema only, not generated candidate tests'}))


if __name__=='__main__':main()
