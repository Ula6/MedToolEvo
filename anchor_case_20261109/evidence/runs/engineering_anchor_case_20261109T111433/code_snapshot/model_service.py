"""Switch only this project's single-GPU model service."""
import json,os,re,signal,subprocess,time,urllib.error,urllib.request
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path("/home/supervisor/project/sy/MedToolEvo")
MODELS={"qa":("medtool-qa","qa/Qwen_Qwen3.5-27B-Q4_K_M.gguf"),"builder":("medtool-builder","builder/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf")}
def fetch(path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open("http://127.0.0.1:8001"+path,timeout=3) as f:return json.load(f)
def ensure(role,trace):
 alias,file=MODELS[role];trace=Path(trace);trace.mkdir(parents=True,exist_ok=True)
 try:current={x["id"] for x in fetch("/v1/models")["data"]}
 except urllib.error.URLError:current=set()
 if current=={alias} and fetch("/health").get("status")=="ok":return {"model":alias,"switched":False}
 out=subprocess.check_output(["/usr/bin/ss","-H","-ltnp","sport = :8001"],text=True)
 exe=ROOT/"third_party/llama.cpp/build/bin/llama-server"
 if out.strip():
  if current not in ({"medtool-qa"},{"medtool-builder"}):raise RuntimeError("Foreign service on port 8001")
  pids=set(re.findall(r"pid=(\d+)",out))
  if len(pids)!=1:raise RuntimeError("Ambiguous service owner")
  pid=int(pids.pop());proc=Path(f"/proc/{pid}")
  if proc.stat().st_uid!=os.getuid():raise RuntimeError("Foreign process owner")
  argv=proc.joinpath("cmdline").read_bytes().decode().rstrip("\0").split("\0")
  if Path(argv[0]).resolve()!=exe.resolve() or "--alias" not in argv or argv[argv.index("--alias")+1] not in {v[0] for v in MODELS.values()}:raise RuntimeError("Process identity mismatch")
  os.kill(pid,signal.SIGINT)
  for _ in range(100):
   try:
    reaped,_status=os.waitpid(pid,os.WNOHANG)
    if reaped==pid:break
   except ChildProcessError:pass
   if not proc.exists():break
   try:
    if proc.joinpath("stat").read_text().split(") ",1)[1].split()[0]=="Z":break
   except FileNotFoundError:break
   time.sleep(.2)
  else:raise RuntimeError("Old service did not exit")
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
 log=ROOT/"logs"/(role+"_autonomous_"+stamp+".log")
 cmd=[str(exe),"--model",str(ROOT/"models"/file),"--alias",alias,"--host","127.0.0.1","--port","8001","--n-gpu-layers","99","--ctx-size","16384","--parallel","1","--batch-size","512","--ubatch-size","128","--jinja","--reasoning","off"]
 env=os.environ.copy();prefix=ROOT/"envs/medtoolevo"
 env.update(CUDA_VISIBLE_DEVICES="GPU-eba3c3c9-c259-f90c-b793-98989cb6142b",TMPDIR=str(ROOT/"tmp"),HF_HOME=str(ROOT/"cache/huggingface"),XDG_CACHE_HOME=str(ROOT/"cache"))
 env["LD_LIBRARY_PATH"]=str(prefix/"lib")+":"+str(prefix/"targets/x86_64-linux/lib")+":"+env.get("LD_LIBRARY_PATH","")
 with log.open("x") as f:p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 state={"pid":p.pid,"model":alias,"command":cmd,"log":str(log),"switched":True}
 (trace/("service_"+stamp+".json")).write_text(json.dumps(state,indent=2),encoding="utf-8")
 for i in range(120):
  if p.poll() is not None:raise RuntimeError("Model start failed: "+str(log))
  try:
   if fetch("/health").get("status")=="ok" and alias in {x["id"] for x in fetch("/v1/models")["data"]}:return state
  except (urllib.error.URLError,TimeoutError):pass
  if i and i%10==0:print("Loading "+alias+"...",flush=True)
  time.sleep(1)
 raise RuntimeError("Readiness timeout: "+str(log))
