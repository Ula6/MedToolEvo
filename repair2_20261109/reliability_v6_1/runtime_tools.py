"""Trusted transport for invoking generated tools only inside bwrap."""
import hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path("/home/supervisor/project/sy/MedToolEvo")
def safe(path):
    p=Path(path).resolve()
    if not p.is_relative_to(ROOT):raise ValueError("Outside project root")
    return p
def dump(path,data):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as f:json.dump(data,f,ensure_ascii=False,indent=2)
def call_tool(manifest_path,payload,trace_dir):
    manifest=json.loads(safe(manifest_path).read_text(encoding="utf-8"))
    code=safe(manifest["code_path"])
    if hashlib.sha256(code.read_bytes()).hexdigest()!=manifest["sha256"]:raise ValueError("Tool hash mismatch")
    report=json.loads(safe(manifest["test_report"]).read_text(encoding="utf-8"))
    if report.get("failed")!=0 or not report.get("passed"):raise ValueError("Tool has not passed functional tests")
    d=safe(trace_dir);d.mkdir(parents=True,exist_ok=False)
    dump(d/"input.json",payload)
    cmd=["/usr/bin/timeout","--kill-after=2s","30s","/usr/bin/bwrap",
        "--unshare-all","--unshare-user","--die-with-parent","--new-session",
        "--cap-drop","ALL","--clearenv","--setenv","PATH","/usr/bin:/bin",
        "--ro-bind","/usr","/usr","--ro-bind","/lib","/lib","--ro-bind","/lib64","/lib64",
        "--ro-bind","/etc/ld.so.cache","/etc/ld.so.cache","--proc","/proc","--dev","/dev",
        "--tmpfs","/tmp","--dir","/work",
        "--ro-bind",str(code),"/work/candidate.py",
        "--ro-bind",str(ROOT/"scripts/sandbox_tool_entry.py"),"/work/entry.py",
        "--chdir","/work","/usr/bin/python3","-I","-B","/work/entry.py"]
    t=time.monotonic()
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:out,err=p.communicate(json.dumps(payload,ensure_ascii=False),timeout=40)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,9);out,err=p.communicate()
        dump(d/"process.json",{"status":"timeout","stdout":out,"stderr":err})
        raise RuntimeError("Tool sandbox timeout")
    dump(d/"process.json",{"returncode":p.returncode,"stdout":out,"stderr":err,"elapsed_seconds":time.monotonic()-t,"code_sha256":manifest["sha256"]})
    if p.returncode:raise RuntimeError("Tool sandbox failed: "+err[:500])
    result=json.loads(out);dump(d/"output.json",result)
    return result
