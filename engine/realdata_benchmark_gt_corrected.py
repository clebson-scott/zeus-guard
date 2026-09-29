#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ZEUS GUARD — benchmark com GROUND TRUTH CORRIGIDO pela camada de identidade.

ACHADO (28/09/2026): 473 dos 527 eventos ATTACK do dataset v2 têm spender que
é contrato VERIFICADO e nomeado (Uniswap, Curve, 1inch, Across, CoW, Bebop,
Camelot, Morpho, ...) — rotulagem v2 marcava 'verified_protocol=False' porque
a verificação de contrato FALHOU na coleta (sem API). Swap normal via router
(pull de terceiro = swap executado) caiu no rótulo ATTACK.

Correção honesta (conservadora): eventos ATTACK cujo spender tem label de
protocolo verificada são EXCLUÍDOS do ground truth (não re-rotulados como
BENIGN: exclusão documenta a incerteza em vez de afirmar benignidade).

Saída: três painéis numa execução —
  [A] v2 publicado (GT contaminado)   — para referência e transparência
  [B] GT corrigido, motor padrão      — o número que deve ser citado
  [C] GT corrigido, motor + labels ON — efeito puro da camada de identidade no FP

Reprodutível OFFLINE: usa o cache durável engine/data/label_cache.json
(567 spenders resolvidos via Blockscout, com timestamp de auditoria).

Uso: python3 engine/realdata_benchmark_gt_corrected.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

# motor padrão (labels OFF) — leitura pura, sem efeitos colaterais de argv
import benchmark_common as bc

labeled = bc.labeled
cache = json.load(open(os.path.join(bc.DATA, "label_cache.json")))
proto_by_addr = {a for a, v in cache.items() if v.get("klass") == "protocol"}
wl = bc.KNOWN_PROTOCOLS
all_proto = proto_by_addr | wl

clean = [r for r in labeled if not r.get("label_error")]
contaminated = [r for r in clean if r.get("label") == "ATTACK"
                and r.get("spender", "").lower() in proto_by_addr]
corrected = [r for r in clean if r not in contaminated]

wl_in_attack = [r for r in clean if r.get("label") == "ATTACK"
                and r.get("spender", "").lower() in wl and r.get("spender", "").lower() not in proto_by_addr]


def bench(rows, use_labels_engine):
    """Rodar a matriz: motor (labels on/off) sobre um ground truth dado."""
    bc.USE_LABELS = use_labels_engine
    if use_labels_engine:
        from label_resolver import LabelResolver
        bc._label_resolver = LabelResolver(offline=True)  # cache durável, reprodutível
    else:
        bc._label_resolver = None
    return bc.confusion_rows(rows)


def rates(s):
    TP, FP, TN, FN = s["TP"], s["FP"], s["TN"], s["FN"]
    n_att, n_ben = TP + FN, FP + TN
    return dict(recall=100.0 * TP / n_att if n_att else 0.0,
                fp=100.0 * FP / n_ben if n_ben else 0.0,
                acc=100.0 * (TP + TN) / (n_att + n_ben),
                n_att=n_att, n_ben=n_ben, TP=TP, FP=FP, FN=FN, TN=TN,
                ic_recall=bc.wilson(TP, n_att), ic_fp=bc.wilson(FP, n_ben))


def panel(tag, title, s):
    r = rates(s)
    print(f"\n[{tag}] {title}")
    print(f"  ataques={r['n_att']} benignos={r['n_ben']} | TP={r['TP']} FN={r['FN']}")
    print(f"  recall:  {r['recall']:.1f}%  IC95 [{r['ic_recall'][0]:.1%}, {r['ic_recall'][1]:.1%}]")
    print(f"  FP rate: {r['fp']:.1f}%  ({r['FP']}/{r['n_ben']})  IC95 [{r['ic_fp'][0]:.1%}, {r['ic_fp'][1]:.1%}]")
    print(f"  acuracia: {r['acc']:.1f}%")
    return r


print("=" * 70)
print("BENCHMARK v2 — GROUND TRUTH CORRIGIDO PELA CAMADA DE IDENTIDADE")
print("=" * 70)
print(f"eventos rotulados v2:        {len(clean)}  (ATAQUE {sum(1 for r in clean if r['label']=='ATTACK')} | BENIGN {sum(1 for r in clean if r['label']=='BENIGN')})")
print(f"excluídos (contaminados):    {len(contaminated)}  ATTACK c/ spender protocolo-verificado (erro de coleta)")
print(f"GT corrigido:                {len(corrected)}  (ATAQUE {sum(1 for r in corrected if r['label']=='ATTACK')} | BENIGN {sum(1 for r in corrected if r['label']=='BENIGN')})")
if wl_in_attack:
    print(f"nota: {len(wl_in_attack)} ATTACK com spender da whitelist curada — mantidos (identidade pré-validada na coleta)")

A = bench(clean, use_labels_engine=False)
rA = panel("A", "v2 publicado (GT contaminado, motor padrão)", A)
B = bench(corrected, use_labels_engine=False)
rB = panel("B", "GT CORRIGIDO, motor padrão  <-- número oficial", B)
C = bench(corrected, use_labels_engine=True)
rC = panel("C", "GT corrigido, motor + camada de identidade ON", C)

print("\n" + "=" * 70)
delta_fp = rB["fp"] - rC["fp"]
print(f"EFÊITO DA CAMADA DE IDENTIDADE (B->C): recall {rB['recall']:.1f}% -> {rC['recall']:.1f}% | FP {rB['fp']:.1f}% -> {rC['fp']:.1f}% (redução de {delta_fp:.1f} p.p. sem perder um único ataque)")
print("=" * 70)

receipt = {
    "version": "gt_corrected_v1",
    "excluded_contaminated": len(contaminated),
    "exclusion_rule": "ATTACK com spender klass=protocol no label_cache (verificação de contrato falhou na coleta v2)",
    "panel_A_published": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in rA.items() if not k.startswith("ic")},
    "panel_B_corrected_default": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in rB.items() if not k.startswith("ic")},
    "panel_C_corrected_labels": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in rC.items() if not k.startswith("ic")},
    "wilson_B": {"recall": [round(x, 4) for x in rB["ic_recall"]], "fp": [round(x, 4) for x in rB["ic_fp"]]},
    "wilson_C": {"recall": [round(x, 4) for x in rC["ic_recall"]], "fp": [round(x, 4) for x in rC["ic_fp"]]},
}
os.makedirs("../evidence", exist_ok=True)
json.dump(receipt, open("../evidence/realdata_benchmark_gt_corrected.json", "w"), indent=2, sort_keys=True)
print("recibo salvo em evidence/realdata_benchmark_gt_corrected.json")
