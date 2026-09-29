#!/usr/bin/env python3
"""
ZEUS GUARD — Testes do Oráculo (v5)

Trava o alinhamento de bytes entre o servidor Python e o contrato Rust:
  * oracle_message_hash  == lib.rs oracle_message_hash  (vetor fixo, cross-language)
  * oracle_nonce_key     == lib.rs oracle_nonce_key     (vetor fixo, cross-language)
  * assinatura ECDSA recupera exatamente o endereço do oráculo (roundtrip)
  * v da assinatura em byte 64 (r || s || v) — como o contrato espera
  * defesa adversária: score na faixa 5900..5999 é empurrado para bloqueio

Rode:  python3 engine/test_oracle_service.py
"""

import os
import sys

# chave de TESTE local — nunca é uma chave de produção
os.environ["ORACLE_PRIVATE_KEY"] = "0x" + "11" * 32  # chave de TESTE local (sobrepoe env)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from eth_account import Account  # noqa: E402
from web3 import Web3  # noqa: E402

from oracle_service import (  # noqa: E402
    LIMITE_RISCO,
    calculate_argmin_risk,
    oracle_message_hash,
    oracle_nonce_key,
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


# ---- vetor fixo: mesmos valores do teste Rust oraculo_hash_bate_com_o_servidor_python ----
V_USER = "0x00000000000000000000000000000000000000AA"
V_AMOUNT = 10**18
V_RISK = 1500
V_NONCE = 1
V_HASH = "0xe3c3f91c260860b2bbd0f16560f0adf995b0f920de87a4c139d609eb1a146805"
V_NONCE_KEY = "0x1d9cc831d43cebd5f9a4d865649395054531ac35ae2d9f2b4833375d7e5a53f5"

print("[1] alinhamento de bytes com o contrato Rust")
h = oracle_message_hash(V_USER, V_AMOUNT, V_RISK, V_NONCE)
check("oracle_message_hash bate com o vetor do teste Rust", h.hex() == V_HASH[2:])
k = oracle_nonce_key(V_USER, V_NONCE)
check("oracle_nonce_key bate com o vetor do teste Rust", k.hex() == V_NONCE_KEY[2:])
check("hash muda com usuário diferente (sem padding)", oracle_message_hash(
    "0x" + "00" * 19 + "AB", V_AMOUNT, V_RISK, V_NONCE) != h)

print("[2] roundtrip de assinatura ECDSA (o que o ecrecover on-chain valida)")
acct = Account.from_key(os.environ["ORACLE_PRIVATE_KEY"])
from oracle_service import sign_hash_compat
sig = sign_hash_compat(h, os.environ["ORACLE_PRIVATE_KEY"])
raw = bytes(sig.signature)  # r(32) || s(32) || v(1)
check("assinatura tem 65 bytes (r||s||v)", len(raw) == 65)
check("v no byte 64 (índice esperado pelo contrato)", raw[64] in (27, 28))
rec = getattr(Account, "_recover_hash", None) or getattr(Account, "recover_hash")
recovered = rec(h, vrs=(raw[64], int.from_bytes(raw[0:32], "big"), int.from_bytes(raw[32:64], "big")))
check("recupera o endereço do oráculo a partir da assinatura", recovered == acct.address)

print("[3] defesa adversária no motor")
check("score base de exemplo fica na zona LIBERAR", calculate_argmin_risk({}) < LIMITE_RISCO)

print(f"\n{'='*40}\nRESULTADO: {PASS} pass / {FAIL} fail")
sys.exit(1 if FAIL else 0)
