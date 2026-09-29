#!/usr/bin/env python3
"""ZEUS GUARD v4.2 — dataset real escalado: coleta e rotulagem por desfecho.

Escalona a metodologia original (label_by_outcome.py) para ~10k+ eventos:
  1. Coleta Approvals ERC-20 reais da Arbitrum mainnet em chunks (getLogs).
  2. Classifica spender como EOA/contrato via eth_getCode (batched JSON-RPC).
  3. Captura nonce atual do spender (eth_getTransactionCount).
  4. Rotula por DESFECHO on-chain: pull por terceiro (Transfer from=owner,
     tx.from != owner) na janela de 7200 blocos apos o approve.
  5. Ground truth identico ao original:
     ATTACK  := pulled>0 E spender fora dos protocolos conhecidos E
                (approve ilimitado OU spender EOA com pulled >= 1e6)
     BENIGN  := todo o resto (inclui roteadores DEX legitimos)

Saidas: engine/data/approves_window_v2.json, engine/data/real_labeled_approves_v2.json
Uso: python3 engine/data/collect_approves_v2.py [n_blocos_atras=26000] [fim_atras=10000]
"""
import json, os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor
import requests

RPC = "https://arb1.arbitrum.io/rpc"
APPROVE = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
UNLIMITED = 2**200
WINDOW = 7200

BACK_A = int(sys.argv[1]) if len(sys.argv) > 1 else 26_000
END_BACK = int(sys.argv[2]) if len(sys.argv) > 2 else 10_000
CHUNK = 2_000

KNOWN_PROTOCOLS = {
    "0xc36442b4a4522e871399cd717abdd847ab11fe88",  # Uniswap V3 NonfungiblePositionManager
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",  # Uniswap V3 SwapRouter02
    "0x777777777777aec03fd955926dbf81597e66834c",  # 1inch Router
    "0x111111125421ca6dc452d289314280a0f8842a65",  # 1inch v5
    "0xe592427a0aece92de3edee1f18e0157c05861564",  # Uniswap V3 SwapRouter
}

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = HERE

_id_lock = threading.Lock()
_next_id = [0]

def rpc_batch(calls, max_retries=5):
    """JSON-RPC batch com backoff; returns list of results in order."""
    for attempt in range(max_retries):
        try:
            r = requests.post(RPC, json=calls, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(1.5 * (attempt + 1)); continue
            data = r.json()
            if isinstance(data, list):
                return data
            # resposta unitaria para batch de 1
            return [data]
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return [{"error": {"message": "batch_exhausted_retries"}} for _ in calls]

def rpc(method, params, max_retries=5):
    res = rpc_batch([{"jsonrpc": "2.0", "id": 1, "method": method, "params": params}])
    return res[0]

def hexint(v):
    """str hex ou bytes -> int; '0x' e vazios viram 0."""
    if v is None: return 0
    if isinstance(v, bytes): h = v.hex()
    else: h = v if isinstance(v, str) else v.hex()
    h = h[2:] if h.startswith("0x") else h
    return int(h, 16) if h else 0

def pad(addr):
    return "0x000000000000000000000000" + addr[2:].lower()

# ---------- 1) bloco atual ----------
res = rpc("eth_blockNumber", [])
latest = int(res["result"], 16)
start, end = latest - BACK_A, latest - END_BACK
print(f"bloco atual: {latest} | coletando approvals {start}..{end} "
      f"({(end-start)} blocos, janela de rotulagem {WINDOW} blocos OK)", flush=True)

# ---------- 2) coleta de approvals ----------
approves = []
a = start
while a < end:
    b = min(a + CHUNK, end)
    logs_res = rpc("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "topics": [APPROVE]}])
    logs = logs_res.get("result", [])
    if not isinstance(logs, list):
        print(f"chunk {a}-{b}: {str(logs_res)[:80]}", flush=True)
        time.sleep(2); a += CHUNK; continue
    for lg in logs:
        approves.append({
            "token": lg["address"].lower(),
            "owner": ("0x" + lg["topics"][1][-40:]) if isinstance(lg["topics"][1], str) else ("0x" + lg["topics"][1].hex()[-40:]),
            "spender": ("0x" + lg["topics"][2][-40:]) if isinstance(lg["topics"][2], str) else ("0x" + lg["topics"][2].hex()[-40:]),
            "amount": str(hexint(lg["data"])),
            "block": int(lg["blockNumber"], 16) if isinstance(lg["blockNumber"], str) else lg["blockNumber"],
            "tx": (lg["transactionHash"][2:] if lg["transactionHash"].startswith("0x") else lg["transactionHash"]) if isinstance(lg["transactionHash"], str) else lg["transactionHash"].hex(),
            "selector": "095ea7b3",
        })
    print(f"chunk {a}-{b}: +{len(logs)} (total {len(approves)})", flush=True)
    a += CHUNK

print(f"TOTAL approves coletados: {len(approves)}", flush=True)
json.dump(approves, open(os.path.join(OUT_DIR, "approves_window_v2.json"), "w"))

# ---------- 3) EOA check + nonce dos spenders unicos ----------
spenders = sorted({ap["spender"] for ap in approves})
print(f"spenders unicos: {len(spenders)}", flush=True)

spender_info = {}
B = 50
for bi in range(0, len(spenders), B):
    group = spenders[bi:bi+B]
    batch = []
    for j, sp in enumerate(group):
        batch.append({"jsonrpc": "2.0", "id": j, "method": "eth_getCode", "params": [sp, "latest"]})
        batch.append({"jsonrpc": "2.0", "id": 10**6 + j, "method": "eth_getTransactionCount", "params": [sp, "latest"]})
    by_id = {r_.get("id"): r_ for r_ in rpc_batch(batch) if isinstance(r_, dict)}
    for j, sp in enumerate(group):
        code = (by_id.get(j) or {}).get("result")
        nonce = (by_id.get(10**6 + j) or {}).get("result")
        if code is not None:
            spender_info[sp] = {
                "spender_eoa": 1 if code == "0x" else 0,
                "spender_nonce_at": int(nonce, 16) if isinstance(nonce, str) else None,
            }
    
for ap in approves:
    info = spender_info.get(ap["spender"], {"spender_eoa": 0, "spender_nonce_at": None})
    ap.update(info)

# ---------- 4) rotulagem por desfecho ----------
tx_from_cache = {}
tx_cache_lock = threading.Lock()

def get_tx_from(txh):
    with tx_cache_lock:
        if txh in tx_from_cache:
            return tx_from_cache[txh]
    res = rpc("eth_getTransactionByHash", [txh])
    frm = (res.get("result") or {}).get("from", "").lower()
    with tx_cache_lock:
        tx_from_cache[txh] = frm
    return frm

def label_one(ap):
    out = dict(ap)
    owner, spender, token = ap["owner"], ap["spender"], ap["token"]
    pulled = 0
    try:
        res = rpc("eth_getLogs", [{
            "fromBlock": hex(ap["block"]), "toBlock": hex(ap["block"] + WINDOW),
            "address": token, "topics": [TRANSFER, pad(owner)]}])
        for lg in res.get("result", []):
            blk = int(lg["blockNumber"], 16) if isinstance(lg["blockNumber"], str) else lg["blockNumber"]
            if blk < ap["block"]:
                continue
            txh = lg["transactionHash"][2:] if isinstance(lg["transactionHash"], str) and lg["transactionHash"].startswith("0x") else (lg["transactionHash"] if isinstance(lg["transactionHash"], str) else lg["transactionHash"].hex())
            if get_tx_from(txh) != owner.lower():
                pulled += hexint(lg["data"])
    except Exception as e:
        out["label_error"] = str(e)[:60]
        pulled = -1

    amount = int(ap["amount"])
    unl = amount >= UNLIMITED
    is_proto = spender in KNOWN_PROTOCOLS
    is_eoa = ap.get("spender_eoa", 0) == 1
    out["pulled_by_third_party"] = pulled
    out["approval_unlimited"] = unl
    is_attack = (pulled > 0) and (not is_proto) and (unl or (is_eoa and pulled >= 1_000_000))
    out["label"] = "ATTACK" if is_attack else "BENIGN"
    return out

with ThreadPoolExecutor(max_workers=24) as ex:
    labeled = list(ex.map(label_one, approves))

n_att = sum(1 for r in labeled if r["label"] == "ATTACK")
print(f"rotulagem concluida: {len(labeled)} eventos | ATTACK={n_att} BENIGN={len(labeled)-n_att}", flush=True)
json.dump(labeled, open(os.path.join(OUT_DIR, "real_labeled_approves_v2.json"), "w"))
print("salvo: engine/data/real_labeled_approves_v2.json + approves_window_v2.json", flush=True)
