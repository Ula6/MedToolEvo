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
results=[]
for name,fn in list(globals().items()):
 if name.startswith('test_') and callable(fn):
  try:fn();results.append({'test':name,'status':'PASS'})
  except Exception as e:results.append({'test':name,'status':'FAIL','error':str(e)})
failed=sum(r['status']=='FAIL' for r in results)
print(json.dumps({'passed':len(results)-failed,'failed':failed,'tests':results}))
raise SystemExit(bool(failed))

