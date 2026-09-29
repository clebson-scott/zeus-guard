#!/usr/bin/env python3
"""ZEUS GUARD v4.2 — benchmark do motor QCSN no dataset real ESCALADO (v2).

Metodologia identica ao realdata_benchmark.py, agora sobre o dataset de ~10k+
eventos reais da Arbitrum mainnet (approves_window_v2.json / real_labeled_approves_v2.json).

Extras v2:
  - Intervalos de confiança Wilson 95% para recall, FP e acurácia.
  - Baseline 'ilimitado em EOA' mantido para comparação honesta.

Uso: python3 engine/realdata_benchmark_v2.py [--use-labels]
  --use-labels  camada de identidade: estende o conjunto de protocolos
                conhecidos com labels resolvidas (Blockscout, cache durável
                em engine/data/label_cache.json). Modo padrão permanece
                idêntico ao publicado.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from qcsn_risk_engine import QCSNRiskEngine as QCSNEngine
from benchmark_common import (
    labeled, USE_LABELS, features, wilson, confusion_rows,
)

rows = confusion_rows(labeled)
TP, FP, TN, FN = rows["TP"], rows["FP"], rows["TN"], rows["FN"]
bloq, aler, lib = rows["bloq"], rows["aler"], rows["lib"]
attack_bloq, attack_aler = rows["attack_bloq"], rows["attack_aler"]
third_party_pulls = rows["third_party_pulls"]

n_att = TP + FN
n_ben = FP + TN
recall = 100.0 * TP / n_att if n_att else 0.0
fp_rate = 100.0 * FP / n_ben if n_ben else 0.0
acc = 100.0 * (TP + TN) / (n_att + n_ben)

lo_r, hi_r = wilson(TP, n_att)
lo_f, hi_f = wilson(FP, n_ben)
lo_a, hi_a = wilson(TP + TN, n_att + n_ben)

print("=" * 66)
print("BENCHMARK EM DADOS REAIS v2 (escalado) — Arbitrum mainnet, rotulagem por desfecho")
print("=" * 66)
print(f"[modo]  labels: {'ON (camada de identidade)' if USE_LABELS else 'OFF (padrão publicado)'}")
print(f"eventos reais rotulados:  {len([r for r in labeled if not r.get('label_error')])}  | ataques: {n_att}  | benignos: {n_ben}")
print(f"pulls por terceiro (raw):  {third_party_pulls}")
print(f"distribuicao verdictos:  BLOQUEAR={bloq} | ALERTAR={aler} | LIBERAR={lib}")
print(f"ataques capturados (recall total):  {TP}/{n_att} = {recall:.1f}%")
print(f"  -> acao direta BLOQUEAR:          {attack_bloq}/{n_att}")
print(f"  -> acao preventiva ALERTAR:       {attack_aler}/{n_att}")
print(f"falsos alarmes (FP rate):       {FP}/{n_ben} = {fp_rate:.1f}%")
print(f"acuracia global:                {acc:.1f}%")
print("-" * 66)
print(f"IC95 Wilson — recall:    [{lo_r:.1%}, {hi_r:.1%}]")
print(f"IC95 Wilson — FP rate:   [{lo_f:.1%}, {hi_f:.1%}]")
print(f"IC95 Wilson — acuracia:  [{lo_a:.1%}, {hi_a:.1%}]")
print("=" * 66)

receipt = {
    "version": "v2_scaled",
    "total_events": len([r for r in labeled if not r.get("label_error")]),
    "attacks": n_att,
    "benign": n_ben,
    "recall": round(recall, 1),
    "fp_rate": round(fp_rate, 1),
    "accuracy": round(acc, 1),
    "wilson_95": {
        "recall": [round(lo_r, 4), round(hi_r, 4)],
        "fp_rate": [round(lo_f, 4), round(hi_f, 4)],
        "accuracy": [round(lo_a, 4), round(hi_a, 4)],
    },
    "blocked_direct": attack_bloq,
    "alerted_preventive": attack_aler,
    "labels_mode": "identity-layer" if USE_LABELS else "published-default",
}

os.makedirs("../evidence", exist_ok=True)
out_path = "../evidence/realdata_benchmark_v2.json"
if USE_LABELS:
    out_path = "../evidence/realdata_benchmark_v2_use_labels.json"
json.dump(receipt, open(out_path, "w"), indent=2, sort_keys=True)
print(f"recibo salvo em {out_path[3:]}")
