#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Núcleo compartilhado dos benchmarks de dados reais (v2 e temporal).

Contém: carregamento do dataset, whitelist de protocolos, seletores de
drainer, extração de features CAUSAIS (sem consulta a blocos futuros),
intervalos de confiança Wilson e contagem de matriz de confusão.
Mantido idêntico ao comportamento do realdata_benchmark_v2.py publicado.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

labeled = json.load(open(os.path.join(DATA, "real_labeled_approves_v2.json")))
all_apps = json.load(open(os.path.join(DATA, "approves_window_v2.json")))
all_apps_sorted = sorted(all_apps, key=lambda x: x["block"])

# lista unificada v2: 5 protocolos originais + 9 verificados na rodada red-team
KNOWN_PROTOCOLS = set(json.load(open(os.path.join(DATA, "known_protocols_v2.json"))))
DRAINER_SELECTORS = {
    "0x23b872dd", "0xf2c298be", "0x095ea7b3", "0x2ac28022", "0xd505accf",
    "0x095ea7b3", "0x12054b33", "0xb88d4fde",
}

# modo labels (camada de identidade) — herdado dos argv do processo chamador
USE_LABELS = "--use-labels" in sys.argv
_label_resolver = None
if USE_LABELS:
    from label_resolver import LabelResolver
    _label_resolver = LabelResolver()


def get_causal_token_freq(token_addr, block_num):
    return sum(1 for a in all_apps_sorted if a["token"] == token_addr and a["block"] <= block_num)


def features(r):
    sp = r.get("spender", "").lower()
    is_zero = sp == "0x0000000000000000000000000000000000000000"
    is_known_proto = sp in KNOWN_PROTOCOLS
    if USE_LABELS and not is_known_proto and _label_resolver is not None and not is_zero:
        # camada de identidade: label verificada de protocolo (cache durável)
        is_known_proto = _label_resolver.is_known_protocol(sp)
    is_contract = (r.get("spender_eoa", 0) == 0) or is_known_proto or is_zero

    nonce = r.get("spender_nonce_at")
    tfreq = get_causal_token_freq(r["token"], r["block"])
    unl = r.get("approval_unlimited", False)

    eoa_feature = 0.0 if is_contract else 1.0
    new_feature = (1.0 if nonce is not None and nonce < 5 else (0.5 if nonce is not None and nonce < 50 else 0.0)) if not is_contract else 0.0
    ratio_feature = 1.0 if unl else 0.3

    raw_sel = (r.get("selector") or "").lower()
    if raw_sel and not raw_sel.startswith("0x"):
        raw_sel = "0x" + raw_sel
    sel = raw_sel[:10]
    sel_drainer = 1.0 if (sel in DRAINER_SELECTORS and not is_known_proto) else 0.0

    legit_token = 1.0 if tfreq >= 10 else (0.6 if tfreq >= 2 else 0.3)
    normal_pattern = 1.0 if (is_known_proto or is_zero or not unl) else 0.0

    return [
        1.0, eoa_feature, new_feature, ratio_feature,
        sel_drainer, 0.0, legit_token, normal_pattern,
    ]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - h) / d), min(1.0, (c + h) / d))


def confusion_rows(rows):
    """Gera contadores de confusão para uma lista de eventos rotulados,
    classificados pelo motor QCSN (mesma política do v2: BLOQUEAR/ALERTAR
    contam como captura preventiva)."""
    import numpy as np
    from qcsn_risk_engine import QCSNRiskEngine as QCSNEngine
    engine = QCSNEngine()
    TP = FP = TN = FN = 0
    bloq = aler = lib = 0
    attack_bloq = attack_aler = 0
    third_party_pulls = 0
    for r in rows:
        if r.get("label_error"):
            continue
        pulled = r.get("pulled_by_third_party", 0)
        if pulled > 0:
            third_party_pulls += 1
        actual_attack = r.get("label") == "ATTACK"
        x = features(r)
        name, verdict, p, E = engine.classify(np.array(x))
        if verdict == "BLOQUEAR":
            bloq += 1
        elif verdict == "ALERTAR":
            aler += 1
        else:
            lib += 1
        if actual_attack:
            if verdict == "BLOQUEAR":
                TP += 1; attack_bloq += 1
            elif verdict == "ALERTAR":
                TP += 1; attack_aler += 1
            else:
                FN += 1
        else:
            if verdict in ("BLOQUEAR", "ALERTAR"):
                FP += 1
            else:
                TN += 1
    return dict(TP=TP, FP=FP, TN=TN, FN=FN, bloq=bloq, aler=aler, lib=lib,
                attack_bloq=attack_bloq, attack_aler=attack_aler,
                third_party_pulls=third_party_pulls)


def contaminated_attack_spenders():
    """Spenders de eventos ATTACK contaminados: label de protocolo verificada
    no cache durável (a verificação da coleta v2 falhou p/ eles). Offline."""
    cache = json.load(open(os.path.join(DATA, "label_cache.json")))
    return {a for a, v in cache.items() if v.get("klass") == "protocol"}


def gt_corrected():
    """Dataset v2 com eventos ATTACK contaminados EXCLUÍDOS (não re-rotulados)."""
    bad = contaminated_attack_spenders()
    return [r for r in labeled
            if not r.get("label_error")
            and not (r.get("label") == "ATTACK" and r.get("spender", "").lower() in bad)]
