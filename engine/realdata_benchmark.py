#!/usr/bin/env python3
"""ZEUS GUARD v4 — benchmark do motor de risco em dados REAIS da mainnet.

Dataset: approves ERC-20 reais coletados da Arbitrum mainnet (60k blocos, ~4h),
rotulados pelo DESFECHO on-chain (metodologia sem lista negra):
  - ATTACK                 = approve ilimitado em EOA/unverified seguido de pull por terceiro
  - BENIGN                 = sem pull de ataque na janela (inclui DEX/routers legitimos)
  - pulled_by_third_party  = contagem explitica de pulls executados por terceiro (tx.from != owner)

Features causais (sem vazamento temporal):
  - Apenas o que e computavel ate o bloco da transacao (block <= tx.block).
  - Frequencia do token acumulada estritamente no passado do bloco dentro da janela.

Uso:  python3 engine/realdata_benchmark.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from qcsn_risk_engine import QCSNRiskEngine as QCSNEngine

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
labeled = json.load(open(os.path.join(DATA, "real_labeled_approves.json")))
all_apps = json.load(open(os.path.join(DATA, "approves_window.json")))

# Ordenacao causal para contagem de frequencia historica
all_apps_sorted = sorted(all_apps, key=lambda x: x["block"])

KNOWN_PROTOCOLS = {
    "0xc36442b4a4522e871399cd717abdd847ab11fe88", # Uniswap V3 NonfungiblePositionManager
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45", # Uniswap V3 SwapRouter02
    "0x777777777777aec03fd955926dbf81597e66834c", # 1inch Router
    "0x111111125421ca6dc452d289314280a0f8842a65", # 1inch v5
    "0xe592427a0aece92de3edee1f18e0157c05861564", # Uniswap V3 SwapRouter
}

DRAINER_SELECTORS = {
    "0x23b872dd", # transferFrom(address,address,uint256)
    "0x39509351", # increaseAllowance
    "0xd505accf", # permit
    "0x095ea7b3", # approve
    "0x12054b33", # permit2
    "0xb88d4fde", # safeTransferFrom
}

def get_causal_token_freq(token_addr, block_num):
    """Calcula a frequencia do token usando estritamente historico no dataset (block <= block_num)."""
    return sum(1 for a in all_apps_sorted if a["token"] == token_addr and a["block"] <= block_num)

def features(r):
    sp = r.get("spender", "").lower()
    is_zero = sp == "0x0000000000000000000000000000000000000000"
    is_known_proto = sp in KNOWN_PROTOCOLS
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
        1.0,           # approval
        eoa_feature,   # spender_EOA
        new_feature,   # spender_novo
        ratio_feature, # razao_valor
        sel_drainer,   # selector_drainer
        0.0,           # destino_envenenado
        legit_token,   # token_USDG_legitimo
        normal_pattern # padrao_normal
    ]

engine = QCSNEngine()
TP = FP = TN = FN = 0
third_party_pulls = 0
bloquear_count = alertar_count = liberar_count = 0

for r in labeled:
    sp = r.get("spender", "").lower()
    pulled = r.get("pulled_by_third_party", 0)
    unl = r.get("approval_unlimited", False)

    if pulled > 0:
        third_party_pulls += 1

    actual_attack = r.get("label") == "ATTACK"

    x = features(r)
    archetype, verdict, p, E = engine.classify(np.array(x))

    if verdict == "BLOQUEAR": bloquear_count += 1
    elif verdict == "ALERTAR": alertar_count += 1
    else: liberar_count += 1

    # Politica: BLOQUEAR e ALERTAR acionam protecao/alerta do guardiao
    blocked = verdict in ("BLOQUEAR", "ALERTAR")

    if actual_attack and blocked: TP += 1
    elif actual_attack and not blocked: FN += 1
    elif not actual_attack and blocked: FP += 1
    else: TN += 1

n = TP + FP + TN + FN
print("=" * 66)
print("BENCHMARK EM DADOS REAIS — Arbitrum mainnet, rotulagem por desfecho")
print("=" * 66)
print(f"eventos reais rotulados:  {n}  | ataques: {TP+FN}  | benignos: {TN+FP}")
print(f"pulls por terceiro (raw): {third_party_pulls}")
print(f"distribuicao verdictos:  BLOQUEAR={bloquear_count} | ALERTAR={alertar_count} | LIBERAR={liberar_count}")
print(f"ataques capturados (recall total): {TP}/{TP+FN} = {100*TP/max(1,TP+FN):.1f}%")
print(f"  -> acao direta BLOQUEAR:          {sum(1 for r in labeled if r.get('label')=='ATTACK' and engine.classify(np.array(features(r)))[1]=='BLOQUEAR')}/{TP+FN}")
print(f"  -> acao preventiva ALERTAR:       {sum(1 for r in labeled if r.get('label')=='ATTACK' and engine.classify(np.array(features(r)))[1]=='ALERTAR')}/{TP+FN}")
print(f"falsos alarmes (FP rate):       {FP}/{FP+TN} = {100*FP/max(1,FP+TN):.1f}%")
print(f"acuracia global:                {100*(TP+TN)/max(1,n):.1f}%")
print("-" * 66)

# Baseline de comparacao (regra cega 'ilimitado em EOA nao auditado')
bTP = sum(1 for r in labeled if r.get("label") == "ATTACK" and (r.get("approval_unlimited") and r.get("spender_eoa")))
bFP = sum(1 for r in labeled if r.get("label") != "ATTACK" and (r.get("approval_unlimited") and r.get("spender_eoa")))
print(f"baseline 'ilimitado em EOA':    recall {100*bTP/max(1,TP+FN):.1f}% | FP {100*bFP/max(1,FP+TN):.1f}%")
print()
print("Labels de ground truth e limitacoes do benchmark:")
print("  1. ATTACK                 = approve ilimitado em EOA/unverified seguido de pull por terceiro")
print("  2. BENIGN                 = sem pull de ataque na janela (inclui DEX/routers legitimos)")
print("  3. Window Right-Censoring = 7200 blocos (~30min na Arbitrum); ataques apos a janela sao truncados")
print("  4. Feature Token Freq     = acumulada sobre a janela de amostragem de ~60k blocos (~1.5 dias)")
