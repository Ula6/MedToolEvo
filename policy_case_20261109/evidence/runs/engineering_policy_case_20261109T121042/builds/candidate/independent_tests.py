import copy,json,runpy,resource
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
FN=runpy.run_path('/work/candidate.py')['run']
CASES=json.loads('[{"input": {"evidence": [{"evidence_id": "e", "text": "A B C"}, {"evidence_id": "f", "text": "A B C"}], "entries": [{"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}, {"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "T", "polarity": "positive", "scope": "S"}, {"name": "B", "group_id": "B", "evidence_id": "e", "quote": "B", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}], "policy": {"scope": "S", "all_of": [{"relation": "R", "polarity": "positive"}, {"relation": "T", "polarity": "positive"}], "any_of": [], "none_of": []}}, "expected": {"entities": [{"name": "A", "evidence_ids": ["e"]}], "unique_entity_count": 1}}, {"input": {"evidence": [{"evidence_id": "e", "text": "A B C"}, {"evidence_id": "f", "text": "A B C"}], "entries": [{"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}, {"name": "B", "group_id": "B", "evidence_id": "e", "quote": "B", "eligible": true, "relation": "T", "polarity": "positive", "scope": "S"}, {"name": "C", "group_id": "C", "evidence_id": "e", "quote": "C", "eligible": true, "relation": "U", "polarity": "positive", "scope": "S"}], "policy": {"scope": "S", "all_of": [], "any_of": [{"relation": "R", "polarity": "positive"}, {"relation": "T", "polarity": "positive"}], "none_of": []}}, "expected": {"entities": [{"name": "A", "evidence_ids": ["e"]}, {"name": "B", "evidence_ids": ["e"]}], "unique_entity_count": 2}}, {"input": {"evidence": [{"evidence_id": "e", "text": "A B C"}, {"evidence_id": "f", "text": "A B C"}], "entries": [{"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}, {"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "T", "polarity": "negative", "scope": "S"}, {"name": "B", "group_id": "B", "evidence_id": "e", "quote": "B", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}, {"name": "B", "group_id": "B", "evidence_id": "e", "quote": "B", "eligible": true, "relation": "T", "polarity": "positive", "scope": "S"}], "policy": {"scope": "S", "all_of": [{"relation": "R", "polarity": "positive"}, {"relation": "T", "polarity": "negative"}], "any_of": [], "none_of": [{"relation": "T", "polarity": "positive"}]}}, "expected": {"entities": [{"name": "A", "evidence_ids": ["e"]}], "unique_entity_count": 1}}, {"input": {"evidence": [{"evidence_id": "e", "text": "A B C"}, {"evidence_id": "f", "text": "A B C"}], "entries": [{"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "R", "polarity": "unknown", "scope": "S"}, {"name": "B", "group_id": "B", "evidence_id": "e", "quote": "B", "eligible": true, "relation": "R", "polarity": "negative", "scope": "S"}], "policy": {"scope": "S", "all_of": [{"relation": "R", "polarity": "negative"}], "any_of": [], "none_of": []}}, "expected": {"entities": [{"name": "B", "evidence_ids": ["e"]}], "unique_entity_count": 1}}, {"input": {"evidence": [{"evidence_id": "e", "text": "A B C"}, {"evidence_id": "f", "text": "A B C"}], "entries": [{"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}, {"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "T", "polarity": "positive", "scope": "Z"}], "policy": {"scope": "S", "all_of": [{"relation": "R", "polarity": "positive"}, {"relation": "T", "polarity": "positive"}], "any_of": [], "none_of": []}}, "expected": {"entities": [], "unique_entity_count": 0}}, {"input": {"evidence": [{"evidence_id": "e", "text": "A B C"}, {"evidence_id": "f", "text": "A B C"}], "entries": [{"name": "B", "group_id": "B", "evidence_id": "e", "quote": "B", "eligible": true, "relation": "U", "polarity": "positive", "scope": "S"}, {"name": "A", "group_id": "A", "evidence_id": "f", "quote": "A", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}, {"name": "B", "group_id": "B", "evidence_id": "f", "quote": "B", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}, {"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "T", "polarity": "positive", "scope": "S"}, {"name": "B", "group_id": "B", "evidence_id": "e", "quote": "B", "eligible": true, "relation": "T", "polarity": "positive", "scope": "S"}, {"name": "A", "group_id": "A", "evidence_id": "f", "quote": "A", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}], "policy": {"scope": "S", "all_of": [{"relation": "R", "polarity": "positive"}, {"relation": "T", "polarity": "positive"}], "any_of": [], "none_of": []}}, "expected": {"entities": [{"name": "B", "evidence_ids": ["f", "e"]}, {"name": "A", "evidence_ids": ["f", "e"]}], "unique_entity_count": 2}}, {"input": {"evidence": [{"evidence_id": "e", "text": "A B C"}, {"evidence_id": "f", "text": "A B C"}], "entries": [{"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}, {"name": "B", "group_id": "B", "evidence_id": "e", "quote": "B", "eligible": true, "relation": "T", "polarity": "positive", "scope": "S"}, {"name": "C", "group_id": "C", "evidence_id": "e", "quote": "C", "eligible": true, "relation": "R", "polarity": "unknown", "scope": "S"}], "policy": {"scope": "S", "all_of": [], "any_of": [], "none_of": [{"relation": "T", "polarity": "positive"}]}}, "expected": {"entities": [{"name": "A", "evidence_ids": ["e"]}], "unique_entity_count": 1}}, {"input": {"evidence": [{"evidence_id": "e", "text": "A B C"}, {"evidence_id": "f", "text": "A B C"}], "entries": [{"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}, {"name": "B", "group_id": "B", "evidence_id": "e", "quote": "does not exist", "eligible": false, "relation": "R", "polarity": "positive", "scope": "S"}], "policy": {"scope": "S", "all_of": [{"relation": "R", "polarity": "positive"}], "any_of": [], "none_of": []}}, "expected_error": "ValueError"}, {"input": {"evidence": [{"evidence_id": "e", "text": "A B C"}, {"evidence_id": "f", "text": "A B C"}], "entries": [{"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "polarity": "positive", "scope": "S"}], "policy": {"scope": "S", "all_of": [{"relation": "R", "polarity": "positive"}], "any_of": [], "none_of": []}}, "expected_error": "ValueError"}, {"input": {"evidence": [{"evidence_id": "e", "text": "A"}], "entries": [{"name": "A", "group_id": "A", "evidence_id": "e", "quote": "A", "eligible": true, "relation": "R", "polarity": "positive", "scope": "S"}], "policy": {"scope": "S", "all_of": [{"relation": "R", "polarity": "unknown"}], "any_of": [], "none_of": []}}, "expected_error": "ValueError"}, {"input": {"evidence": [{"evidence_id": "E1", "text": "Symbol A was observed in relation R1 with positive polarity."}, {"evidence_id": "E2", "text": "Symbol B was observed in relation R2 with negative polarity."}, {"evidence_id": "E3", "text": "Symbol C was observed in relation R1 with positive polarity."}], "entries": [{"name": "Entity_Alpha", "group_id": "G1", "evidence_id": "E1", "quote": "Symbol A was observed in relation R1 with positive polarity.", "eligible": true, "relation": "R1", "polarity": "positive", "scope": "SCOPE_X"}, {"name": "Entity_Alpha", "group_id": "G1", "evidence_id": "E2", "quote": "Symbol B was observed in relation R2 with negative polarity.", "eligible": true, "relation": "R2", "polarity": "negative", "scope": "SCOPE_X"}, {"name": "Entity_Beta", "group_id": "G2", "evidence_id": "E3", "quote": "Symbol C was observed in relation R1 with positive polarity.", "eligible": true, "relation": "R1", "polarity": "positive", "scope": "SCOPE_Y"}], "policy": {"scope": "SCOPE_X", "all_of": [{"relation": "R1", "polarity": "positive"}], "any_of": [], "none_of": [{"relation": "R2", "polarity": "negative"}]}}, "expected": {"entities": [], "unique_entity_count": 0}}, {"input": {"evidence": [{"evidence_id": "E4", "text": "Symbol S1 is present in relation R_A."}, {"evidence_id": "E5", "text": "Symbol S2 is absent in relation R_B."}, {"evidence_id": "E6", "text": "Symbol S3 is present in relation R_C."}], "entries": [{"name": "Group_Missing", "group_id": "G3", "evidence_id": "E4", "quote": "Symbol S1 is present in relation R_A.", "eligible": true, "relation": "R_A", "polarity": "positive", "scope": "SCOPE_Z"}, {"name": "Group_ExplicitNeg", "group_id": "G4", "evidence_id": "E5", "quote": "Symbol S2 is absent in relation R_B.", "eligible": true, "relation": "R_B", "polarity": "negative", "scope": "SCOPE_Z"}, {"name": "Group_ExplicitNeg", "group_id": "G4", "evidence_id": "E6", "quote": "Symbol S3 is present in relation R_C.", "eligible": true, "relation": "R_C", "polarity": "positive", "scope": "SCOPE_Z"}], "policy": {"scope": "SCOPE_Z", "all_of": [], "any_of": [{"relation": "R_A", "polarity": "positive"}, {"relation": "R_B", "polarity": "negative"}], "none_of": [{"relation": "R_B", "polarity": "negative"}]}}, "expected": {"entities": [{"name": "Group_Missing", "evidence_ids": ["E4"]}], "unique_entity_count": 1}}]')
def check_case(index):
 c=CASES[index]; payload=copy.deepcopy(c['input']); original=copy.deepcopy(payload)
 try: out=FN(payload)
 except ValueError:
  assert c.get('expected_error')=='ValueError',repr(c)
  assert payload==original,'Input mutated on rejection'
  return
 assert 'expected' in c,'Expected ValueError for '+repr(c)
 assert payload==original,'Input mutated for '+repr(c)
 assert out==c['expected'],'Input='+repr(original)+' expected='+repr(c['expected'])+' actual='+repr(out)
 assert FN(copy.deepcopy(original))==out,'Nondeterministic result'
 json.dumps(out,allow_nan=False)

def test_case_00():
 check_case(0)

def test_case_01():
 check_case(1)

def test_case_02():
 check_case(2)

def test_case_03():
 check_case(3)

def test_case_04():
 check_case(4)

def test_case_05():
 check_case(5)

def test_case_06():
 check_case(6)

def test_case_07():
 check_case(7)

def test_case_08():
 check_case(8)

def test_case_09():
 check_case(9)

def test_case_10():
 check_case(10)

def test_case_11():
 check_case(11)


# Exact old test definitions, imports and helpers retained below.
import copy,json,runpy
run=runpy.run_path('/work/candidate.py')['run']
def entry(name='Alpha',group='g1',eligible=True,quote='Alpha binds',eid='e1'):
 return dict(name=name,group_id=group,eligible=eligible,quote=quote,evidence_id=eid)
def packet(entries):return {'evidence':[{'evidence_id':'e1','text':'Alpha binds Beta. A is Alpha.'},{'evidence_id':'e2','text':'Alpha binds again.'}],'entries':entries}
def check(p):
 b=copy.deepcopy(p);r=run(p);assert p==b;assert set(r)=={'entities','unique_entity_count'};assert r['unique_entity_count']==len(r['entities']);json.dumps(r);return r
def bad(p):
 try:run(p)
 except ValueError:return
 raise AssertionError('Invalid input accepted: '+repr(p))
def test_empty():assert check(packet([]))=={'entities':[],'unique_entity_count':0}
def test_positive():assert check(packet([entry()]))=={'entities':[{'name':'Alpha','evidence_ids':['e1']}],'unique_entity_count':1}
def test_negative_filtered():assert check(packet([entry(eligible=False)]))['entities']==[]
def test_group_and_provenance():
 r=check(packet([entry(),entry(quote='Alpha binds again.',eid='e2'),entry()]))
 assert r['entities']==[{'name':'Alpha','evidence_ids':['e1','e2']}]
def test_distinct_order():assert [e['name'] for e in check(packet([entry('Beta','b',quote='Beta'),entry()]))['entities']]==['Beta','Alpha']
def test_bad_quote():bad(packet([entry(quote='Alpha cures')]))
def test_bad_source():bad(packet([entry(eid='missing')]))
def test_strict_boolean():bad(packet([entry(eligible='true')]))
def test_conflicting_group_name():bad(packet([entry(),entry('Beta',quote='Beta')]))
def test_atomic_and_schema():
 for p in [None,{},packet([entry(),{}]),packet([entry(name=' ')]),{'entries':[],'evidence':[{'evidence_id':'e1','text':'A'},{'evidence_id':'e1','text':'B'}]}]:bad(p)

if __name__=='__main__':
 results=[]
 for name,fn in sorted(list(globals().items())):
  if name.startswith('test_') and callable(fn):
   try: fn(); results.append({'test':name,'status':'PASS'})
   except Exception as exc: results.append({'test':name,'status':'FAIL','error':type(exc).__name__+': '+str(exc)})
 failed=sum(x['status']=='FAIL' for x in results)
 print(json.dumps({'tests':results,'passed':len(results)-failed,'failed':failed}))
 raise SystemExit(1 if failed else 0)
