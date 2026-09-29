#!/usr/bin/env python3
"""Popula o cache de labels com todos os spenders do dataset v2 (uso único)."""
import json, time, sys
sys.path.insert(0, "/app/conversations/6ab97c2b7f5a926229c1a96d/zg/engine")
from label_resolver import LabelResolver

lab = json.load(open("/app/conversations/6ab97c2b7f5a926229c1a96d/zg/engine/data/real_labeled_approves_v2.json"))
sp = sorted(set(r.get("spender", "").lower() for r in lab
                if not r.get("label_error") and r.get("spender")))
r = LabelResolver()
t0 = time.time(); fresh = 0; errs = 0
for a in sp:
    if a in r._cache:
        continue
    try:
        r.resolve(a, use_network=True)
        fresh += 1
    except Exception as e:
        errs += 1
        print("ERR", a, str(e)[:60], flush=True)
print(f"resolvidos {fresh} novos | erros {errs} | {time.time()-t0:.0f}s")
classes = {}
for v in r._cache.values():
    classes[v["klass"]] = classes.get(v["klass"], 0) + 1
print("classes:", classes)
wl = set(json.load(open("/app/conversations/6ab97c2b7f5a926229c1a96d/zg/engine/data/known_protocols_v2.json")))
print("protocolos rotulados fora da whitelist:")
for v in r._cache.values():
    if v["klass"] == "protocol" and v["address"] not in wl:
        print("  ", v["address"], "->", v["name"], "|", v["source"])
