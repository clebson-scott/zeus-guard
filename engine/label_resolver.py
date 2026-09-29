#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
Label Resolver — Identidade de contratos | ZEUS GUARD (módulo de produção)
================================================================================
Lição estrutural do falso positivo "Permit2Proxy" (28/09/2026): rotular por
desfecho on-chain (padrão de fluxo) sem camada de IDENTIDADE gera FP em massa.
Este módulo é a camada de identidade: resolve o nome/label de um contrato
antes de o motor de risco classificar o fluxo.

Fontes (em ordem, com cache durável em engine/data/label_cache.json):
1. Cache local (resoluções anteriores — repositório, offline, instantâneo).
2. Whitelist curada do projeto (engine/data/known_protocols_v2.json).
3. Blockscout Arbitrum (API aberta, sem chave): nome do contrato verificado,
   flags de proxy/verificação. Fallback Blockscout Ethereum L1.

Fail-honesto: sem rede → classe "unknown" com source="unresolved"; NUNCA
inventa label. Cache registra fonte e timestamp para auditoria.
================================================================================
Uso:
    python3 engine/label_resolver.py 0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae
    python3 engine/label_resolver.py 0x... 0x...   (lote)
    python3 engine/label_resolver.py --stats
"""
import json
import os
import sys
import time
from dataclasses import dataclass, asdict

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE_PATH = os.path.join(DATA, "label_cache.json")

BLOCKSCOUT_HOSTS = {
    "arbitrum": "https://arbitrum.blockscout.com",
    "ethereum": "https://eth.blockscout.com",
}
HTTP_TIMEOUT = 20


def _norm(addr) -> str:
    a = (addr or "").strip().lower()
    if not a.startswith("0x") or len(a) != 42:
        return ""
    try:
        int(a[2:], 16)
    except ValueError:
        return ""
    return a


@dataclass
class Label:
    address: str
    name: str = ""               # nome canônico do contrato (ex.: 'LiFiDiamond')
    klass: str = "unknown"       # protocol | eoa | contract_unverified | unknown
    source: str = "unresolved"   # cache | whitelist | blockscout-arbitrum | blockscout-ethereum
    verified: bool = False
    proxy: bool = False
    fetched_at: float = 0.0

    def as_dict(self):
        return asdict(self)


class LabelResolver:
    def __init__(self, cache_path=CACHE_PATH, offline=False):
        self.cache_path = cache_path
        self.offline = offline
        self._cache = {}
        self._wl = set()
        self._load()

    # ---------------- persistência ----------------
    def _load(self):
        if os.path.exists(self.cache_path):
            try:
                self._cache = json.load(open(self.cache_path))
            except Exception:
                self._cache = {}
        wl = os.path.join(DATA, "known_protocols_v2.json")
        if os.path.exists(wl):
            try:
                self._wl = set(_norm(a) for a in json.load(open(wl)))
            except Exception:
                self._wl = set()

    def _save(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        json.dump(self._cache, open(self.cache_path, "w"), indent=1, sort_keys=True)

    def stats(self):
        return {
            "cached": len(self._cache),
            "whitelist": len(self._wl),
            "by_class": {
                k: sum(1 for v in self._cache.values() if v.get("klass") == k)
                for k in ("protocol", "eoa", "contract_unverified", "unknown")
            },
        }

    # ---------------- fontes remotas ----------------
    def _blockscout(self, addr: str):
        for chain, host in BLOCKSCOUT_HOSTS.items():
            try:
                r = requests.get(f"{host}/api/v2/addresses/{addr}", timeout=HTTP_TIMEOUT)
                if r.status_code != 200:
                    continue
                j = r.json()
                name = (j.get("name") or "").strip()
                verified = bool(j.get("is_verified"))
                proxy = bool(j.get("proxy_type"))
                if not j.get("is_contract"):
                    return Label(addr, klass="eoa", source=f"blockscout-{chain}",
                                 fetched_at=time.time())
                if name and verified:
                    return Label(addr, name=name, klass="protocol",
                                 source=f"blockscout-{chain}", verified=True,
                                 proxy=proxy, fetched_at=time.time())
                # contrato sem verificação/nome
                return Label(addr, name=name, klass="contract_unverified",
                             source=f"blockscout-{chain}", verified=verified,
                             proxy=proxy, fetched_at=time.time())
            except Exception:
                continue
        return None

    # ---------------- API pública ----------------
    def resolve(self, address: str, use_network: bool = True) -> dict:
        addr = _norm(address)
        if not addr:
            return Label("", klass="unknown", source="invalid-address").as_dict()

        cached = self._cache.get(addr)
        if cached:
            return cached

        if addr in self._wl:
            lab = Label(addr, klass="protocol", source="whitelist",
                        fetched_at=time.time())
        elif self.offline or not use_network:
            lab = Label(addr)
        else:
            lab = self._blockscout(addr) or Label(addr)

        self._cache[addr] = lab.as_dict()
        self._save()
        return lab.as_dict()

    def resolve_many(self, addresses):
        return [self.resolve(a) for a in addresses]

    def is_known_protocol(self, address: str) -> bool:
        """Resposta rápida para o motor: spender/contrato é protocolo conhecido
        (whitelist curada ou label verificada)."""
        addr = _norm(address)
        if not addr:
            return False
        if addr in self._wl:
            return True
        return self.resolve(addr).get("klass") == "protocol"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv):
    if "--stats" in argv:
        r = LabelResolver(offline=True)
        print(json.dumps(r.stats(), indent=2))
        return 0
    addrs = [a for a in argv[1:] if a.startswith("0x")]
    if not addrs:
        print(__doc__)
        return 1
    r = LabelResolver()
    for lab in r.resolve_many(addrs):
        print("%-44s %-22s %-9s %s%s" % (
            lab["address"], (lab["name"] or "-")[:22], lab["klass"], lab["source"],
            " [proxy]" if lab["proxy"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
