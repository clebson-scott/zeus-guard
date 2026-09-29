#!/usr/bin/env python3
"""Scan Arbitrum blocks for real Across V3 calldata (fillV3Relay / depositV3)."""
import requests, json, threading, time

RPC = "https://arb1.arbitrum.io/rpc"
SELS = {"0xc39ffe76": "fillV3Relay", "0x7d0ece9c": "depositV3"}
OUT = "/app/conversations/6ab97c2b7f5a926229c1a96d/zg/engine/data/across_real_hits.json"

lock = threading.Lock()
hits = []

def latest():
    r = requests.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}, timeout=20).json()
    return int(r["result"], 16)

def scan(bn, stats):
    try:
        b = requests.post(RPC, json={"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber",
                                     "params": [hex(bn), True]}, timeout=20).json().get("result")
        stats["ok"] += 1
        if not b:
            return
        for tx in b.get("transactions", []):
            s = tx.get("input", "0x")[:10].lower()
            if s in SELS:
                with lock:
                    hits.append({"name": SELS[s], "hash": tx["hash"], "from": tx["from"],
                                 "to": tx["to"], "cd": tx["input"], "block": bn})
                    json.dump(hits, open(OUT, "w"))
    except Exception:
        stats["err"] += 1

def worker(lo, k, n, N, stats):
    for bn in range(lo + k, n + 1, N):
        if len(hits) >= 12:
            return
        scan(bn, stats)

def main():
    n = latest()
    stats = {"ok": 0, "err": 0}
    NTHREADS = 10
    WINDOW = 20000
    lo = n - WINDOW
    threads = [threading.Thread(target=worker, args=(lo, k, n, NTHREADS, stats)) for k in range(NTHREADS)]
    t0 = time.time()
    for t in threads: t.start()
    for t in threads: t.join()
    print(f"window {WINDOW} blocks in {time.time()-t0:.0f}s | ok={stats['ok']} err={stats['err']}")
    print(f"hits: {len(hits)}")
    for h in hits:
        print(" ", h["name"], h["hash"][:22], "block", h["block"])

if __name__ == "__main__":
    main()
