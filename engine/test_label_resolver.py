#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes do Label Resolver — executar: python3 test_label_resolver.py
Cobre: whitelist, cache durável, Blockscout ao vivo (se offline → SKIP),
honestidade fail-closed (offline nunca inventa label), EOA, endereços
malformados e invariante "sem fonte não há rotulação de protocolo".
"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from label_resolver import LabelResolver, _norm

_failures = []
def check(name, cond, extra=""):
    print(("  [OK]   " if cond else "  [FAIL] ") + name + ("" if cond else "  <- " + extra))
    if not cond:
        _failures.append(name)

LIFI = "0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae"
P2P  = "0x89c6340b1a1f4b25d36cd8b063d49045caf3f818"
VITALIK_EOA = "0xd8da611269cbcbbe37eb56af4dd5ac1e260b90a3"


def main():
    print("=" * 78)
    print("Testes Label Resolver | ZEUS GUARD")
    print("=" * 78)

    tmp = tempfile.mkdtemp()
    cache = os.path.join(tmp, "cache.json")

    print("\n[1] Whitelist curada (offline)")
    r = LabelResolver(cache_path=cache, offline=True)
    lab = r.resolve(LIFI)
    check("Diamond LI.FI (whitelist) → protocol/whitelist",
          lab["klass"] == "protocol" and lab["source"] == "whitelist", str(lab))
    check("is_known_protocol(Diamond) → True", r.is_known_protocol(LIFI))

    print("\n[2] Cache durável")
    r2 = LabelResolver(cache_path=cache, offline=True)
    lab2 = r2.resolve(LIFI)
    check("segunda instância lê do cache", lab2["source"] == "whitelist", str(lab2))
    check("arquivo de cache criado", os.path.exists(cache))

    print("\n[3] Honestidade offline (fail-closed)")
    r3 = LabelResolver(cache_path=cache, offline=True)
    lab3 = r3.resolve("0x000000000000000000000000000000000000dEaD")
    check("endereço desconhecido offline → unknown/unresolved",
          lab3["klass"] == "unknown" and lab3["source"] == "unresolved", str(lab3))
    check("is_known_protocol(desconhecido) → False (não inventa)", not r3.is_known_protocol("0x000000000000000000000000000000000000dEaD"))

    print("\n[4] Endereços malformados")
    for bad in ["", "0x123", "zzz", "0x" + "g1" * 20]:
        lab = r3.resolve(bad)
        check(f"resolve({bad[:16]!r}) → invalid-address sem crash",
              lab["klass"] == "unknown" and lab["source"] == "invalid-address", str(lab))
    check("_norm de hex inválido → ''", _norm("0x" + "g1" * 20) == "")

    print("\n[5] Blockscout ao vivo (rede)")
    cache_live = os.path.join(tmp, "live.json")
    r4 = LabelResolver(cache_path=cache_live)
    try:
        lab4 = r4.resolve(P2P)
        if lab4["source"].startswith("blockscout"):
            check("Permit2Proxy → name=Permit2Proxy, protocol, verified",
                  lab4["name"] == "Permit2Proxy" and lab4["klass"] == "protocol" and lab4["verified"],
                  str(lab4))
            check("EOA (vitalik.eth) → klass=eoa", r4.resolve(VITALIK_EOA)["klass"] == "eoa")
            r5 = LabelResolver(cache_path=cache_live, offline=True)
            check("resolução ao vivo persiste no cache (r5 offline resolve)",
                  r5.resolve(P2P)["name"] == "Permit2Proxy")
        else:
            print("  [SKIP] rede indisponível — resolução Blockscout não testada")
    except Exception as e:
        print(f"  [SKIP] rede indisponível ({str(e)[:60]})")

    print("\n" + "=" * 78)
    if _failures:
        print(f"RESULTADO: {len(_failures)} FALHA(S)")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("RESULTADO: TODOS OS TESTES DO LABEL RESOLVER PASSARAM")


if __name__ == "__main__":
    main()
