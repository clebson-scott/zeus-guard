#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZEUS GUARD — validação temporal do benchmark (split por bloco).

Motivação: o número agregado do benchmark v2 pode esconder deriva temporal
(mudanças de padrão de ataque, concentração de FPs num período, efeito de
rotulagem retroativa). Este script divide o dataset no ponto mediano de
BLOCO (metade inicial vs metade final da janela ~1,5 dias) e reporta as
métricas de cada período com IC95 Wilson.

Leitura honesta:
  - Features continuam CAUSAIS (frequência de token acumulada só com blocos
    <= bloco do evento) — o split não altera a causalidade, apenas separa
    períodos.
  - A whitelist de protocolos é identidade ESTÁTICA (mesma nos dois
    períodos); o split expõe se o desempenho depende do período.
  - Flag --use-labels disponível para a camada de identidade (idem v2).

Uso: python3 engine/realdata_benchmark_temporal.py [--use-labels]
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from benchmark_common import labeled, USE_LABELS, wilson, confusion_rows, gt_corrected
USE_GT_CORRECTED = "--gt-corrected" in sys.argv

if USE_GT_CORRECTED:
    clean = gt_corrected()
else:
    clean = [r for r in labeled if not r.get("label_error")]
blocks = sorted(r["block"] for r in clean)
median_block = blocks[len(blocks) // 2]

early = [r for r in clean if r["block"] < median_block]
late = [r for r in clean if r["block"] >= median_block]


def period_stats(rows, name):
    s = confusion_rows(rows)
    TP, FP, TN, FN = s["TP"], s["FP"], s["TN"], s["FN"]
    n_att, n_ben = TP + FN, FP + TN
    recall = 100.0 * TP / n_att if n_att else 0.0
    fp_rate = 100.0 * FP / n_ben if n_ben else 0.0
    acc = 100.0 * (TP + TN) / (n_att + n_ben) if (n_att + n_ben) else 0.0
    return dict(name=name, n_att=n_att, n_ben=n_ben, TP=TP, FP=FP, TN=TN, FN=FN,
                recall=recall, fp_rate=fp_rate, acc=acc,
                wilson_recall=wilson(TP, n_att), wilson_fp=wilson(FP, n_ben),
                wilson_acc=wilson(TP + TN, n_att + n_ben),
                verdicts=dict(BLOQUEAR=s["bloq"], ALERTAR=s["aler"], LIBERAR=s["lib"]))


E = period_stats(early, "metade inicial")
L = period_stats(late, "metade final")


def show(S):
    print(f"\n--- {S['name'].upper()} ---")
    print(f"eventos: {S['n_att']+S['n_ben']}  (ataques {S['n_att']} | benignos {S['n_ben']})")
    print(f"verdictos: BLOQUEAR={S['verdicts']['BLOQUEAR']} | ALERTAR={S['verdicts']['ALERTAR']} | LIBERAR={S['verdicts']['LIBERAR']}")
    print(f"recall:    {S['recall']:.1f}%  IC95 [{S['wilson_recall'][0]:.1%}, {S['wilson_recall'][1]:.1%}]  (FN={S['FN']})")
    print(f"FP rate:   {S['fp_rate']:.1f}%  IC95 [{S['wilson_fp'][0]:.1%}, {S['wilson_fp'][1]:.1%}]  ({S['FP']}/{S['n_ben']})")
    print(f"acuracia:  {S['acc']:.1f}%  IC95 [{S['wilson_acc'][0]:.1%}, {S['wilson_acc'][1]:.1%}]")


print("=" * 70)
print("VALIDAÇÃO TEMPORAL — split por bloco mediano (sem re-treino, features causais)")
print("=" * 70)
print(f"janela: blocos {blocks[0]}..{blocks[-1]} | mediana do split: bloco {median_block}")
print(f"[GT]     {'CORRIGIDO (contaminados excluídos)' if USE_GT_CORRECTED else 'v2 original (contaminado)'}")
print(f"[modo]  labels: {'ON (camada de identidade)' if USE_LABELS else 'OFF (padrão publicado)'}")
show(E)
show(L)

# estabilidade: recall de 100% nos dois períodos e FP com ICs sobrepostos?
recall_stable = (E["FN"] == 0 and L["FN"] == 0)
fp_overlap = (E["wilson_fp"][0] <= L["wilson_fp"][1]) and (L["wilson_fp"][0] <= E["wilson_fp"][1])
print("\n" + "-" * 70)
print(f"estabilidade recall (FN=0 nos dois períodos): {'SIM' if recall_stable else 'NÃO'}")
print(f"estabilidade FP (IC95 dos períodos se sobrepõem): {'SIM' if fp_overlap else 'NÃO'}")
print("-" * 70)

receipt = {
    "version": "temporal_split_v1",
    "median_block": median_block,
    "labels_mode": "identity-layer" if USE_LABELS else "published-default",
    "early": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in E.items() if k != "wilson_recall"},
    "early_wilson": {k: [round(x, 4) for x in v] for k, v in E.items() if k.startswith("wilson")},
    "late": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in L.items() if k != "wilson_recall"},
    "late_wilson": {k: [round(x, 4) for x in v] for k, v in L.items() if k.startswith("wilson")},
    "recall_stable": recall_stable,
    "fp_stable": fp_overlap,
}
os.makedirs("../evidence", exist_ok=True)
out = "../evidence/realdata_benchmark_temporal.json"
if USE_LABELS:
    out = "../evidence/realdata_benchmark_temporal_use_labels.json"
json.dump(receipt, open(out, "w"), indent=2, sort_keys=True)
print(f"recibo salvo em {out[3:]}")
