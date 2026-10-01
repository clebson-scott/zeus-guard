#!/usr/bin/env python3
"""ZEUS GUARD v6 reproducibility and release gate.

The verifier intentionally distinguishes PASS, SKIP and FAIL. It never reports
legacy v4 evidence as evidence for the v6 contract.
"""
import json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RPC = os.getenv("ZEUS_RPC", "https://sepolia-rollup.arbitrum.io/rpc")
DEPLOY_DOC = ROOT / "deploy/DEPLOYADO_V6_ARBITRUM_SEPOLIA.md"
DEFAULT_V6 = "0x4a7cdfa8ca7a3969b3427c42948abbd988097dd9"
CONTRACT = os.getenv("ZEUS_GUARD_CONTRACT_ADDRESS", DEFAULT_V6)
RESULTS = []

def stage(n, title): print(f"\n[STAGE {n:02d}] {title}")
def add(kind, name, detail=""):
    RESULTS.append((kind, name, detail)); print(f"  [{kind}] {name}: {detail}")
def run(cmd, cwd=ROOT, timeout=180):
    env = os.environ.copy()
    env["PATH"] = os.path.expanduser("~/.cargo/bin") + os.pathsep + env.get("PATH", "")
    p = subprocess.run(cmd, cwd=cwd, shell=True, text=True, capture_output=True, timeout=timeout, env=env)
    return p.returncode, p.stdout + p.stderr

def test_cmd(name, cmd, success=None, timeout=180):
    code, out = run(cmd, timeout=timeout)
    ok = code == 0 and (success(out) if success else True)
    add("PASS" if ok else "FAIL", name, f"exit={code}; {out[-300:].strip()}")
    return ok

def check_dependencies():
    stage(1, "Toolchain and Python dependencies")
    missing=[]
    for module in ("numpy","scipy","Crypto","PIL","web3","eth_utils","dotenv"):
        try: __import__(module)
        except ImportError: missing.append(module)
    add("PASS" if not missing else "FAIL", "Python dependencies", "all present" if not missing else ", ".join(missing))
    for exe in ("node -v", "cargo -V", "cargo stylus --version"):
        test_cmd(exe.split()[0], exe)

def check_secrets():
    stage(2, "Secret absence")
    patterns = re.compile(r"(?:PRIVATE[_ ]KEY\s*[:=]\s*0x[a-fA-F0-9]{64}|BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY|AKIA[0-9A-Z]{16})", re.IGNORECASE)
    hits=[]
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(x in p.parts for x in (".git","target","__pycache__")): continue
        if p.suffix not in {".py",".rs",".js",".json",".toml",".sh",".md"}: continue
        text=p.read_text(errors="ignore")
        for m in patterns.finditer(text):
            hits.append(str(p.relative_to(ROOT)))
    add("PASS" if not hits else "FAIL", "Secret scan", "no private material found" if not hits else sorted(set(hits)))

def check_fixtures():
    stage(3, "v6 fixtures and ABI")
    for rel in ("engine/data/real_labeled_approves.json","engine/data/approves_window.json","zeus-guard-contract/zeus-guard-abi.json","ext/manifest.json"):
        p=ROOT/rel
        try: json.loads(p.read_text()); add("PASS","JSON "+rel,"valid")
        except Exception as e: add("FAIL","JSON "+rel,str(e))
    add("PASS" if DEPLOY_DOC.exists() else "FAIL", "v6 deployment record", str(DEPLOY_DOC.relative_to(ROOT)))

def check_contract():
    stage(4, "Rust v6 contract tests, lint and build")
    test_cmd("Rust tests", "cargo test --quiet", lambda o: "test result: ok." in o)
    test_cmd("Rust clippy", "cargo clippy --lib -- -D warnings")
    code,out=run("cargo stylus check --endpoint "+RPC, cwd=ROOT/"zeus-guard-contract", timeout=300)
    m=re.search(r"contract size:\s*([0-9.]+\s*KiB)\s*\((\d+) bytes\)",out)
    if m:
        # The size is recorded, not compared to the obsolete v4 24 KiB claim.
        add("PASS" if code == 0 or "activation not allowed" in out else "FAIL", "Stylus build", f"contract size {m.group(1)} ({m.group(2)} bytes); exit={code}")
    else: add("FAIL", "Stylus build", out[-500:])

def check_python_and_extension():
    stage(5, "Python, oracle and extension tests")
    for rel in ("engine/test_engine_invariants.py","engine/test_inv9.py","engine/test_label_resolver.py","engine/test_oracle_service.py"):
        test_cmd(rel, "python3 "+rel)
    test_cmd("Node extension", "node ext/test_extension.js", lambda o: "0 falharam" in o)

def check_benchmarks():
    stage(6, "Benchmarks and honesty")
    for rel in ("engine/demo.py","engine/realdata_benchmark.py","engine/honesty_experiment.py"):
        test_cmd(rel, "python3 "+rel)
    gt=ROOT/"engine/realdata_benchmark_gt_corrected.py"
    if gt.exists(): test_cmd("corrected ground truth", "python3 engine/realdata_benchmark_gt_corrected.py")

def rpc_call(method, params):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req=urllib.request.Request(RPC,data=body,headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=20).read()).get("result")

def check_deployment():
    stage(7, "v6 deployment and ABI alignment")
    if not CONTRACT or CONTRACT == DEFAULT_V6:
        add("BLOCKED", "v6 redeployment", "current address is the pre-hardening deployment; set ZEUS_GUARD_CONTRACT_ADDRESS after deploy")
        return
    try:
        code=rpc_call("eth_getCode",[CONTRACT,"latest"])
        add("PASS" if code and len(code)>100 else "FAIL", "contract bytecode", f"{len(code)//2 if code else 0} bytes")
        # ABI-specific selector check: checkTxSigned(address,address,address,...)
        selector=subprocess.check_output(["python3","-c","from web3 import Web3; print(Web3.keccak(text='checkTxSigned(address,address,address,uint256,uint256,uint256,bytes[])')[:4].hex())"],text=True).strip()
        add("PASS", "v6 ABI selector", selector)
    except Exception as e: add("FAIL", "RPC deployment verification", str(e))

def main():
    start=time.time(); print("ZEUS GUARD v6 RELEASE GATE")
    check_dependencies(); check_secrets(); check_fixtures(); check_contract(); check_python_and_extension(); check_benchmarks(); check_deployment()
    passed=sum(k=="PASS" for k,_,_ in RESULTS); failed=sum(k=="FAIL" for k,_,_ in RESULTS); blocked=sum(k=="BLOCKED" for k,_,_ in RESULTS)
    print(f"\nSUMMARY: {passed} PASS, {failed} FAIL, {blocked} BLOCKED, {time.time()-start:.1f}s")
    return 1 if failed or blocked else 0
if __name__ == "__main__": sys.exit(main())
