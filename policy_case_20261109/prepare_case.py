"""Freeze a different real-source task: signed relation conjunction, exclusion and scope."""
import hashlib
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'citation_case_20261109/code'))
from citation_oracle import oracle as citations


def source_packet(item,labels):
    xml=item['xml'];sid=item['source_id']
    parsed=citations({'sources':[{'source_id':sid,'xml':xml}]})['groups']
    brackets=[m.group() for m in re.finditer(r'\[[^\[\]]*\]',xml) if 'ref-type="bibr"' in m.group()]
    assert len(parsed)==len(brackets)==len(labels)
    groups=[]
    for i,(g,q) in enumerate(zip(parsed,brackets,strict=True)):
        groups.append({'group_id':'g'+str(i+1),'evidence_id':sid+':g'+str(i+1),
                       'members':g['reference_ids'],'quote':q})
    return {'source_id':sid,'doc_hop_id':item['task_id'],'xml':xml,'groups':groups,
            'source_sha256':hashlib.sha256(xml.encode()).hexdigest(),
            'source_url':item['url']},dict(zip([g['group_id'] for g in groups],labels,strict=True))


def literal(relation,polarity='positive'):return {'relation':relation,'polarity':polarity}


def main():
    raw=json.loads((HERE.parent/'citation_case_20261109/public_sources.json').read_text(encoding='utf-8'))
    main_labels=[('diagnostic_bm','positive'),('differential_mm','positive'),('differential_bone_island','positive'),
        ('differential_tuberculosis','positive'),('primary_lung','positive'),('primary_prostate','positive'),
        ('primary_site_reported','negative'),('primary_gastric','positive'),('human_comparison','positive'),
        ('modality_mri','positive'),('modality_ct','positive'),('external_validation','positive'),('internal_validation','positive')]
    reuse_labels=[('direct_comparison','positive'),('celecoxib','positive'),('joins','positive'),
                  ('short_followup','positive'),('mid_followup','positive'),('bias_blinding','positive'),('bias_other','positive')]
    first,private=source_packet(raw[0],main_labels);second,private2=source_packet(raw[2],reuse_labels)
    scope=first['source_id']
    def query(qid,all_of,any_of=(),none_of=()):
        def term(t):return literal(*t) if isinstance(t,tuple) else literal(t)
        return {'query_id':qid,'policy':{'scope':scope,'all_of':[term(t) for t in all_of],
            'any_of':[term(t) for t in any_of],'none_of':[term(t) for t in none_of]}}
    queries=[query('q1',['modality_ct','external_validation'],none_of=['internal_validation']),
        query('q2',['modality_mri','external_validation']),
        query('q3',['modality_mri','internal_validation'],none_of=['external_validation']),
        query('q4',['modality_ct','human_comparison']),query('q5',['primary_prostate','modality_mri']),
        query('q6',[('primary_site_reported','negative'),'modality_ct']),
        query('q7',[('primary_site_reported','negative'),'external_validation']),
        query('q8',['differential_mm','modality_ct']),
        query('q9',['human_comparison'],any_of=['modality_ct','modality_mri'],none_of=['external_validation']),
        query('q10',['modality_ct',('primary_site_reported','negative')],none_of=['external_validation']),
        query('q11',['modality_mri','external_validation'],none_of=['human_comparison']),
        query('q12',['modality_ct','external_validation'],any_of=['primary_gastric',('primary_site_reported','negative')])]
    task={'id':'derived_signed_policy_evolution_20261109','question':
        'For every supplied policy, list study citation IDs and only contributing evidence-group IDs. Apply conjunction, disjunction, explicit signed negation, exclusion and exact document scope. Missing facts are not negative assertions. This indexes the supplied paragraph, not an assertion about the underlying studies or clinical efficacy.',
        'main_source':first,'queries':queries,'reuse_source':second,
        'reuse_queries':[{'query_id':'cross1','policy':{'scope':second['source_id'],'all_of':[literal('celecoxib'),literal('mid_followup')],'any_of':[],'none_of':[literal('joins')]}},
                         {'query_id':'cross2','policy':{'scope':second['source_id'],'all_of':[literal('joins'),literal('short_followup')],'any_of':[],'none_of':[literal('celecoxib')]}}],
        'parent_registry':'/home/supervisor/project/sy/MedToolEvo/runs/ledger_repair_v2_20261108T080249/registry/evidence_ledger.json',
        'manual_intervention':'Researcher-selected source paragraphs, relation vocabulary,12 policies, source-indexed study IDs, independent reference rules and regression criteria fixed before baseline. Qwen labels semantic relations; same labels supplied to all arms. No candidate code handwritten or source edits.',
        'scope':'Development engineering update of existing ledger, not original BioASQ or DocHopQA question',
        'primary_goal':'Actual existing tool cannot satisfy new policy queries; Manager must choose backward-compatible extension; old10tests unchanged. Qwen manual answers reported separately, not assumed inferior.',
        'formal_exclusion':True}
    d=HERE/'data';d.mkdir(exist_ok=True)
    (d/'task.json').write_text(json.dumps(task,ensure_ascii=False,indent=2),encoding='utf-8')
    (d/'private_annotation_audit.json').write_text(json.dumps({'main':private,'reuse':private2},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'sources':[first['source_id'],second['source_id']],'main_groups':len(first['groups']),'queries':len(queries),
                      'reuse_groups':len(second['groups']),'legacy_regression_sha256':hashlib.sha256((HERE/'code/legacy_regression.py').read_bytes()).hexdigest()}))


if __name__=='__main__':main()
