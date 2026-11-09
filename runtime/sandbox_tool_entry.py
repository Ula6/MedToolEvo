import json,resource,runpy,sys
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
resource.setrlimit(resource.RLIMIT_FSIZE,(1024**2,1024**2))
payload=json.load(sys.stdin)
fn=runpy.run_path("/work/candidate.py")["run"]
json.dump(fn(payload),sys.stdout,ensure_ascii=False,allow_nan=False)
