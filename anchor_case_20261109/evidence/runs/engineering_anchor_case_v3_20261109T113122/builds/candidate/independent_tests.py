import copy,json,runpy,resource
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
FN=runpy.run_path('/work/candidate.py')['run']
CASES=json.loads('[{"input": {"sources": [{"source_id": "s1", "text": "Hello World"}], "queries": [{"query_id": "q1", "text": "World"}]}, "expected": {"queries": [{"query_id": "q1", "matches": [{"source_id": "s1", "start": 6, "end": 11, "quote": "World"}]}], "unsupported_query_ids": []}}, {"input": {"sources": [{"source_id": "s1", "text": "ana"}], "queries": [{"query_id": "q1", "text": "ana"}]}, "expected": {"queries": [{"query_id": "q1", "matches": [{"source_id": "s1", "start": 0, "end": 3, "quote": "ana"}]}], "unsupported_query_ids": []}}, {"input": {"sources": [{"source_id": "s1", "text": "Straße"}], "queries": [{"query_id": "q1", "text": "ss"}, {"query_id": "q2", "text": "s"}]}, "expected": {"queries": [{"query_id": "q1", "matches": [{"source_id": "s1", "start": 4, "end": 5, "quote": "ß"}]}, {"query_id": "q2", "matches": [{"source_id": "s1", "start": 0, "end": 1, "quote": "S"}]}], "unsupported_query_ids": []}}, {"input": {"sources": [{"source_id": "s1", "text": "Hello\u3000World"}], "queries": [{"query_id": "q1", "text": "Hello World"}]}, "expected": {"queries": [{"query_id": "q1", "matches": [{"source_id": "s1", "start": 0, "end": 11, "quote": "Hello\u3000World"}]}], "unsupported_query_ids": []}}, {"input": {"sources": [{"source_id": "s1", "text": "Test"}, {"source_id": "s2", "text": "Test"}], "queries": [{"query_id": "q1", "text": "Test"}]}, "expected": {"queries": [{"query_id": "q1", "matches": [{"source_id": "s1", "start": 0, "end": 4, "quote": "Test"}, {"source_id": "s2", "start": 0, "end": 4, "quote": "Test"}]}], "unsupported_query_ids": []}}, {"input": {"sources": [], "queries": [{"query_id": "q1", "text": "Nothing"}]}, "expected": {"queries": [{"query_id": "q1", "matches": []}], "unsupported_query_ids": ["q1"]}}, {"input": {"sources": [{"source_id": "s1", "text": "A"}, {"source_id": "s1", "text": "B"}], "queries": [{"query_id": "q1", "text": "A"}]}, "expected_error": "ValueError"}, {"input": {"sources": [{"source_id": "s1", "text": "A"}], "queries": [{"query_id": "q1", "text": "   "}]}, "expected_error": "ValueError"}, {"input": {"sources": [{"source_id": "S", "text": "aaa"}], "queries": [{"query_id": "Q", "text": "aa"}]}, "expected": {"queries": [{"query_id": "Q", "matches": [{"source_id": "S", "start": 0, "end": 2, "quote": "aa"}, {"source_id": "S", "start": 1, "end": 3, "quote": "aa"}]}], "unsupported_query_ids": []}}, {"input": {"sources": [{"source_id": "S", "text": "ß"}], "queries": [{"query_id": "Q", "text": "ss"}]}, "expected": {"queries": [{"query_id": "Q", "matches": [{"source_id": "S", "start": 0, "end": 1, "quote": "ß"}]}], "unsupported_query_ids": []}}, {"input": {"sources": [{"source_id": "S", "text": "ß"}], "queries": [{"query_id": "Q", "text": "s"}]}, "expected": {"queries": [{"query_id": "Q", "matches": []}], "unsupported_query_ids": ["Q"]}}, {"input": {"sources": [{"source_id": "S", "text": "XＡ\\t \xa0Bz"}], "queries": [{"query_id": "Q", "text": "a b"}]}, "expected": {"queries": [{"query_id": "Q", "matches": [{"source_id": "S", "start": 1, "end": 6, "quote": "Ａ\\t \xa0B"}]}], "unsupported_query_ids": []}}, {"input": {"sources": [{"source_id": "S", "text": "D‐blind"}], "queries": [{"query_id": "Q", "text": "D-blind"}]}, "expected": {"queries": [{"query_id": "Q", "matches": []}], "unsupported_query_ids": ["Q"]}}]')
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

def test_case_12():
 check_case(12)

if __name__=='__main__':
 results=[]
 for name,fn in sorted(list(globals().items())):
  if name.startswith('test_') and callable(fn):
   try: fn(); results.append({'test':name,'status':'PASS'})
   except Exception as exc: results.append({'test':name,'status':'FAIL','error':type(exc).__name__+': '+str(exc)})
 failed=sum(x['status']=='FAIL' for x in results)
 print(json.dumps({'tests':results,'passed':len(results)-failed,'failed':failed}))
 raise SystemExit(1 if failed else 0)
