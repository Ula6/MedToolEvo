import copy,json,runpy,resource
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
FN=runpy.run_path('/work/candidate.py')['run']
CASES=json.loads('[{"input": {"rows": [{"value": 2.0, "weight": 1.0}, {"value": 8.0, "weight": 1.0}]}, "expected": {"weighted_mean": 5.0, "weighted_population_variance": 9.0, "weighted_population_sd": 3.0, "weighted_geometric_mean": 4.0}}, {"input": {"rows": [{"value": 10.0, "weight": 5.0}]}, "expected": {"weighted_mean": 10.0, "weighted_population_variance": 0.0, "weighted_population_sd": 0.0, "weighted_geometric_mean": 10.0}}, {"input": {"rows": [{"value": 100.0, "weight": 0.0}, {"value": 200.0, "weight": 2.0}]}, "expected": {"weighted_mean": 200.0, "weighted_population_variance": 0.0, "weighted_population_sd": 0.0, "weighted_geometric_mean": 200.0}}, {"input": {"rows": []}, "expected_error": "ValueError"}, {"input": {"rows": [{"value": "5.0", "weight": 1.0}]}, "expected_error": "ValueError"}, {"input": {"rows": [{"value": 5.0, "weight": -2.0}]}, "expected_error": "ValueError"}, {"input": {"rows": [{"value": 0.0, "weight": 1.0}]}, "expected_error": "ValueError"}, {"input": {"rows": [{"value": 10.0, "weight": 0.0}, {"value": 20.0, "weight": 0.0}]}, "expected_error": "ValueError"}]')
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

if __name__=='__main__':
 results=[]
 for name,fn in sorted(list(globals().items())):
  if name.startswith('test_') and callable(fn):
   try: fn(); results.append({'test':name,'status':'PASS'})
   except Exception as exc: results.append({'test':name,'status':'FAIL','error':type(exc).__name__+': '+str(exc)})
 failed=sum(x['status']=='FAIL' for x in results)
 print(json.dumps({'tests':results,'passed':len(results)-failed,'failed':failed}))
 raise SystemExit(1 if failed else 0)
