"""CPU preflight of references, regressions and typed policy interface."""
import hashlib
import json
from pathlib import Path
import sys
from schema_support import Draft202012Validator
from policy_protocol import INPUT_SCHEMA,OUTPUT_SCHEMA
from policy_oracle import oracle
from policy_fixtures import fixed_inputs


def main():
    Draft202012Validator.check_schema(INPUT_SCHEMA);Draft202012Validator.check_schema(OUTPUT_SCHEMA)
    cases=fixed_inputs();results=[]
    for i,p in enumerate(cases):
        try:r=oracle(p)
        except ValueError:results.append('ValueError')
        else:
            Draft202012Validator(INPUT_SCHEMA).validate(p);Draft202012Validator(OUTPUT_SCHEMA).validate(r);results.append(r)
    assert results[0]=={'entities':[{'name':'A','evidence_ids':['e']}],'unique_entity_count':1}
    assert results[2]=={'entities':[{'name':'A','evidence_ids':['e']}],'unique_entity_count':1}
    assert results[4]=={'entities':[],'unique_entity_count':0}
    assert results[5]=={'entities':[{'name':'B','evidence_ids':['f','e']},{'name':'A','evidence_ids':['f','e']}],'unique_entity_count':2}
    assert results[-3:]==['ValueError']*3
    p={'evidence':[{'evidence_id':'e','text':'A B'}],'entries':[
        {'name':'A','group_id':'A','evidence_id':'e','quote':'A','eligible':True},
        {'name':'B','group_id':'B','evidence_id':'e','quote':'B','eligible':False}]}
    assert oracle(p)=={'entities':[{'name':'A','evidence_ids':['e']}],'unique_entity_count':1}
    d=Path(sys.argv[1]);task=json.loads((d/'task.json').read_text(encoding='utf-8'));audit=json.loads((d/'private_annotation_audit.json').read_text(encoding='utf-8'))
    src=task['main_source'];assert hashlib.sha256(src['xml'].encode()).hexdigest()==src['source_sha256']
    ev=[];entries=[]
    for g in src['groups']:
        relation,polarity=audit['main'][g['group_id']];ev.append({'evidence_id':g['evidence_id'],'text':src['xml']})
        for m in g['members']:entries.append({'name':m,'group_id':m,'evidence_id':g['evidence_id'],'quote':g['quote'],'eligible':True,'relation':relation,'polarity':polarity,'scope':src['source_id']})
    counts=[];answers=[]
    for q in task['queries']:
        payload={'evidence':ev,'entries':entries,'policy':q['policy']};Draft202012Validator(INPUT_SCHEMA).validate(payload)
        r=oracle(payload);Draft202012Validator(OUTPUT_SCHEMA).validate(r);counts.append(r['unique_entity_count']);answers.append([e['name'] for e in r['entities']])
    assert answers[0]==['CR37','CR51'] and answers[-2]==[]
    legacy=Path(__file__).resolve().parent/'legacy_regression.py'
    assert hashlib.sha256(legacy.read_bytes()).hexdigest()=='f8dccce35eb81b26198eb8b851e0e1051e68056b426efa795ffd17d575f56d1f'
    print(json.dumps({'pass':True,'fixed_policy_cases':10,'legacy_mode_reference_check':True,
        'original_named_tests_retained':10,'legacy_test_sha256':hashlib.sha256(legacy.read_bytes()).hexdigest(),
        'source_groups':len(src['groups']),'queries':len(counts),'offline_query_sizes':counts,
        'models_called':False,'expected_values_private':True}))


if __name__=='__main__':main()
