#!/usr/bin/env python3
"""
ZEUS GUARD — Testes do Oraculo (v6)

Trava o contrato de seguranca da v6 entre o servidor Python e o contrato Rust:
  * [1] hash com DOMAIN SEPARATION == lib.rs oracle_message_hash (vetor fixo, 192 bytes)
  * [2] nonce key anti-replay == lib.rs oracle_nonce_key (vetor fixo)
  * [3] MULTISIG: 2 assinaturas distintas, ambas recuperam oraculos diferentes
  * [4] MOTOR REAL: argmin deterministico sobre as 8 features (sem stub)
  * [5] DEFESA ADVERSARIA: faixa 59.x% e empurrada para bloqueio
  * [6] INTEGRIDADE: argmin == Gibbs (o servico fail-closed se divergir)

Rode:  python3 engine/test_oracle_service.py
"""

import os
import sys

# chaves de TESTE local — nunca sao chaves de producao
os.environ["ORACLE_PRIVATE_KEY_1"] = "0x" + "11" * 32
os.environ["ORACLE_PRIVATE_KEY_2"] = "0x" + "22" * 32
os.environ["ORACLE_PRIVATE_KEY_3"] = "0x" + "33" * 32
os.environ["ZEUS_CONTRACT_ADDRESS"] = "0x00000000000000000000000000000000000000C0"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
from eth_account import Account  # noqa: E402

from oracle_service import (  # noqa: E402
    LIMITE_RISCO,
    THRESHOLD,
    calculate_risk,
    oracle_message_hash,
    oracle_nonce_key,
    sign_hash_compat,
)

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✔ {name}")
    else:
        FAIL += 1
        print(f"  ✘ {name}")


# ---- vetores fixos: mesmos valores dos testes Rust v6 ----
V_USER = "0x00000000000000000000000000000000000000AA"
V_TOKEN = "0x00000000000000000000000000000000000000D0"
V_PAYEE = "0x00000000000000000000000000000000000000EE"
V_CONTRACT = "0x00000000000000000000000000000000000000C0"
V_AMOUNT = 10**18
V_RISK = 1500
V_NONCE = 1
V_HASH = "0x0569bd23eb4abed6c5ca842d14360222d04cc20fc523026d17931c9939791015"
V_NONCE_KEY = "0x1d9cc831d43cebd5f9a4d865649395054531ac35ae2d9f2b4833375d7e5a53f5"

print("[1] domain separation — alinhamento de bytes com o Rust v6")
h = oracle_message_hash(V_USER, V_TOKEN, V_PAYEE, 421614, V_CONTRACT, V_AMOUNT, V_RISK, V_NONCE)
check("hash v6 bate com o vetor do teste Rust", h.hex() == V_HASH[2:])
h_chain = oracle_message_hash(V_USER, V_TOKEN, V_PAYEE, 421615, V_CONTRACT, V_AMOUNT, V_RISK, V_NONCE)
h_deploy = oracle_message_hash(V_USER, V_TOKEN, V_PAYEE, 421614, "0x00000000000000000000000000000000000000C1", V_AMOUNT, V_RISK, V_NONCE)
h_token = oracle_message_hash(V_USER, "0x00000000000000000000000000000000000000D1", V_PAYEE, 421614, V_CONTRACT, V_AMOUNT, V_RISK, V_NONCE)
h_payee = oracle_message_hash(V_USER, V_TOKEN, "0x00000000000000000000000000000000000000EF", 421614, V_CONTRACT, V_AMOUNT, V_RISK, V_NONCE)
h_user = oracle_message_hash("0x00000000000000000000000000000000000000AB", V_TOKEN, V_PAYEE, 421614, V_CONTRACT, V_AMOUNT, V_RISK, V_NONCE)
check("outra chain => outro hash (replay cross-chain morto)", h != h_chain)
check("outro deploy => outro hash (replay cross-deploy morto)", h != h_deploy)
check("outro token => outro hash", h != h_token)
check("outro payee => outro hash", h != h_payee)
check("outro user => outro hash", h != h_user)

print("[2] nonce key — anti-replay deterministico")
k = oracle_nonce_key(V_USER, V_NONCE)
check("nonce key bate com o vetor do teste Rust", k.hex() == V_NONCE_KEY[2:])
check("nonce novo => chave nova", oracle_nonce_key(V_USER, 2) != k)

print("[3] multisig 2-de-3 — o que o ecrecover on-chain vai validar")
keys = [Account.from_key(os.environ[f"ORACLE_PRIVATE_KEY_{i}"]) for i in (1, 2, 3)]
raws, sigs = [], []
for kt in keys[:3]:
    sig = sign_hash_compat(h, kt.key)
    raw = bytes(sig.signature)  # r(32) || s(32) || v(1)
    raws.append(raw)
    sigs.append(raw.hex())
check("3 assinaturas de 65 bytes (r||s||v)", all(len(r) == 65 for r in raws))
rec = getattr(Account, "_recover_hash", None) or getattr(Account, "recover_hash")
recovered = [
    rec(h, vrs=(r[64], int.from_bytes(r[0:32], "big"), int.from_bytes(r[32:64], "big")))
    for r in raws
]
check("cada assinatura recupera o oraculo que assinou", recovered == [k.address for k in keys[:3]])
check("oraculos distintos (threshold 2 exige 2 chaves diferentes)", len(set(recovered)) == 3)
check("servico carrega threshold 2", THRESHOLD == 2)

print("[4] motor REAL — argmin deterministico sobre as 8 features")
drainer = calculate_risk(np.array([1.0, 0.9, 0.8, 0.9, 0.9, 0.4, 0.2, 0.0]))
check("vetor DRAINER_APPROVE => BLOQUEAR (9500)", drainer["name"] == "DRAINER_APPROVAL" and drainer["risk_x100"] >= LIMITE_RISCO)
legit = calculate_risk(np.array([1.0, 0.0, 0.1, 0.3, 0.0, 0.0, 0.8, 0.9]))
check("vetor LEGIT_APPROVE => LIBERAR (<= 3000)", legit["name"] == "LEGIT_APPROVE" and legit["risk_x100"] <= 3000)
risky = calculate_risk(np.array([0.7, 0.3, 0.4, 0.5, 0.0, 0.0, 0.6, 0.5]))
check("vetor RISKY_BUT_LEGIT => ALERTAR (5500, abaixo do limiar)", risky["name"] == "RISKY_BUT_LEGIT" and risky["risk_x100"] == 5500 and risky["risk_x100"] < LIMITE_RISCO)
noise = np.array([1.0, 0.0, 0.1, 0.3, 0.0, 0.0, 0.8, 0.9]) + np.random.default_rng(7).normal(0, 0.05, 8)
check("argmin e deterministico sob ruido moderado (LEGIT_APPROVE)", calculate_risk(np.clip(noise, 0, 1))["name"] == "LEGIT_APPROVE")

print("[5] defesa adversaria — zona 59.x% vira bloqueio")
class _FakeResult(dict):
    pass
# injeta score na faixa de raspagem e verifica o empurrao
import oracle_service  # noqa: E402
orig = oracle_service.verdict_to_risk_x100
try:
    oracle_service.verdict_to_risk_x100 = lambda name, p: 5975  # invasor mimetizando o limite
    pushed = oracle_service.calculate_risk(np.array([1.0, 0.9, 0.8, 0.9, 0.9, 0.4, 0.2, 0.0]))
    check("score 5975 e empurrado para >= 6000 (BLOQUEAR)", pushed["risk_x100"] >= LIMITE_RISCO)
finally:
    oracle_service.verdict_to_risk_x100 = orig

print("[6] integridade argmin == Gibbs (fail-closed)")
check("argmin e Gibbs concordam no vetor LEGIT (experimento da honestidade)", calculate_risk(np.array([0.0, 0.5, 0.2, 0.4, 0.0, 0.0, 0.95, 0.8]))["name"] == "LEGIT_PAYMENT")

print(f"\n{'='*40}\nRESULTADO: {PASS} pass / {FAIL} fail")
sys.exit(1 if FAIL else 0)
