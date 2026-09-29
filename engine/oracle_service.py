#!/usr/bin/env python3
"""
ZEUS GUARD — Servidor do Oráculo Analítico (v5)

Assina criptograficamente o score de risco ANTES da transação chegar à carteira.
A assinatura é verificada on-chain por check_tx_signed (zeus-guard-contract/src/lib.rs)
via precompile ecrecover — nenhum atacante consegue forjar um score "liberado".

ALINHAMENTO DE BYTES (CRÍTICO):
    hash = keccak256( user(20 bytes, SEM padding) || amount(32 BE) || risk(32 BE) || nonce(32 BE) )
Esta é a concatenação crua da função `oracle_message_hash` do contrato Rust.
Codificações eth_abi (que fazem padding do address para 32 bytes) NÃO batem com o
contrato — o teste engine/test_oracle_service.py trava o vetor contra regressão.

Configuração:
    1. python3 generate_keys.py            # gera o par de chaves do oráculo
    2. coloque ORACLE_PRIVATE_KEY=0x... no .env desta pasta (NUNCA comite o .env)
    3. python3 engine/oracle_service.py    # sobe em :8080
    4. init_oracle(endereco_publico) no contrato
"""

import os

from dotenv import load_dotenv
from eth_account import Account
from flask import Flask, jsonify, request
from web3 import Web3

load_dotenv()

app = Flask(__name__)

PRIVATE_KEY = os.environ.get("ORACLE_PRIVATE_KEY")
if not PRIVATE_KEY:
    raise ValueError(
        "ERRO CRÍTICO: defina ORACLE_PRIVATE_KEY no .env "
        "(gere com python3 generate_keys.py; nunca comite este arquivo)"
    )
oracle_account = Account.from_key(PRIVATE_KEY)

LIMITE_RISCO = 6000  # 60% em x100 — espelha RISK_BLOCK_X100 do contrato


def sign_hash_compat(message_hash, private_key):
    """Assina um hash cru (keccak) — API de acordo com a versão do eth-account."""
    fn = (
        getattr(Account, "unsafe_sign_hash", None)
        or getattr(Account, "_sign_hash", None)
        or getattr(Account, "signHash")
    )
    return fn(message_hash, private_key)


def oracle_message_hash(user_address: str, amount: int, risk_score: int, nonce: int) -> bytes:
    """Espelha byte a byte a função oracle_message_hash do contrato Rust (v5).

    user entra com 20 bytes crus — exatamente como user.as_slice() no Rust.
    """
    user20 = bytes.fromhex(Web3.to_checksum_address(user_address)[2:])
    return Web3.keccak(
        user20
        + amount.to_bytes(32, "big")
        + risk_score.to_bytes(32, "big")
        + nonce.to_bytes(32, "big")
    )


def oracle_nonce_key(user_address: str, nonce: int) -> bytes:
    """Espelha oracle_nonce_key do Rust — chave de anti-replay on-chain."""
    user20 = bytes.fromhex(Web3.to_checksum_address(user_address)[2:])
    return Web3.keccak(user20 + nonce.to_bytes(32, "big"))


def calculate_argmin_risk(tx_data: dict) -> int:
    """Motor analítico argmin real (troque a saída de exemplo pela chamada do
    qcsn_risk_engine / honesty_experiment em produção).

    [DEFESA ADVERSÁRIA]: se o invasor mimetizar o limite para raspar em 59.x%,
    a penalidade empurra a transação para a zona de bloqueio seguro.
    """
    base_score = 1500  # saída do modelo real (exemplo)

    if 5900 <= base_score < LIMITE_RISCO:
        base_score += 150  # vai para 6050+ => veredito BLOQUEAR

    return base_score


@app.route("/score", methods=["POST"])
def get_score():
    data = request.get_json(silent=True) or {}

    user_address = data.get("user", "0x0000000000000000000000000000000000000000")
    amount = int(data.get("amount", 0))
    nonce = int(data.get("nonce", 0))

    risk_score = calculate_argmin_risk(data)

    # hash reconstruído nos MESMOS bytes que o contrato vai reconstruir
    msg_hash = oracle_message_hash(user_address, amount, risk_score, nonce)

    # assinatura ECDSA da identidade confiável do oráculo (r || s || v, 65 bytes)
    signed = sign_hash_compat(msg_hash, PRIVATE_KEY)

    return jsonify(
        {
            "score": risk_score,
            "verdict": "BLOQUEAR" if risk_score >= LIMITE_RISCO else "LIBERAR",
            "signature": signed.signature.hex(),
            "oracle": oracle_account.address,
        }
    )


if __name__ == "__main__":
    # produção: sem debug (evita vazamento de logs/stack com dados sensíveis)
    app.run(port=8080, debug=False)
