#!/usr/bin/env python3
"""
ZEUS GUARD — Servidor do Oráculo Analítico (v6 — Enforcamento Absoluto)

Assina criptograficamente o score de risco ANTES da transacao chegar ao cofre.
A partir da v6, vault_send EXIGE o bundle assinado (threshold 2-de-3): sem
assinaturas validas, o cofre nao move dinheiro.

NOVIDADES v6:
  * DOMAIN SEPARATION — o hash assinado inclui chain_id e o endereco do contrato
    (espelho exato do eth_abi.encode de 192 bytes que o Rust reconstrui on-chain):
        keccak256(abi.encode([user, chain_id, amount, risk, nonce, contract]))
    Assinatura capturada NAO vale em outra chain nem em outro deploy.
  * MULTISIG — o servidor assina com 2 chaves distintas (threshold on-chain = 2).
  * MOTOR REAL — sem stub: o score vem do argmin deterministico do
    honesty_experiment.py sobre as 8 features lidas do estado REAL da chain
    via real_features.extract_features (RPC).

Configuracao (.env, NUNCA commitado):
    ORACLE_PRIVATE_KEY_1=0x...        # chave do oraculo 1 (generate_keys.py)
    ORACLE_PRIVATE_KEY_2=0x...        # chave do oraculo 2 (generate_keys.py)
    ORACLE_PRIVATE_KEY_3=0x...        # opcional (3o oraculo)
    ZEUS_RPC=https://sepolia-rollup.arbitrum.io/rpc
    ZEUS_CHAIN_ID=421614
    ZEUS_CONTRACT_ADDRESS=0x...       # endereco do contrato v6 DEPLOYADO

Rodar: python3 engine/oracle_service.py   (porta 8080, sem debug)
"""

import os

import numpy as np
from dotenv import load_dotenv
from eth_abi import encode
from eth_account import Account
from flask import Flask, jsonify, request
from web3 import Web3

from honesty_experiment import argmin_classify
from qcsn_risk_engine import ARCHETYPES, RISK_OF, QCSNRiskEngine
from real_features import extract_features, verdict_to_risk_x100

load_dotenv()

app = Flask(__name__)

LIMITE_RISCO = 6000  # 60% em x100 — espelha RISK_BLOCK_X100 do contrato
THRESHOLD = 2        # espelha ORACLE_THRESHOLD_MIN do contrato v6

# ---- chaves do multisig (2..3) ----
_ORACLE_KEYS = []
for _i in (1, 2, 3):
    _k = os.environ.get(f"ORACLE_PRIVATE_KEY_{_i}")
    if _k:
        _ORACLE_KEYS.append(Account.from_key(_k))
if len(_ORACLE_KEYS) < THRESHOLD:
    raise ValueError(
        "ERRO CRITICO: defina ORACLE_PRIVATE_KEY_1 e ORACLE_PRIVATE_KEY_2 no .env "
        f"(o contrato v6 exige threshold {THRESHOLD}; gere as chaves com generate_keys.py)"
    )

RPC_URL = os.environ.get("ZEUS_RPC", "https://sepolia-rollup.arbitrum.io/rpc")
CHAIN_ID = int(os.environ.get("ZEUS_CHAIN_ID", "421614"))
CONTRACT_ADDRESS = os.environ.get("ZEUS_CONTRACT_ADDRESS", "")

_PROFILES = np.array([ARCHETYPES[k] for k in ARCHETYPES])
_NAMES = list(ARCHETYPES)

# ---- integridade: o classificador barato tem que concordar com o motor completo ----
_ENGINE = QCSNRiskEngine()


def oracle_message_hash(user_address: str, chain_id: int, contract: str,
                        amount: int, risk_score: int, nonce: int) -> bytes:
    """Espelha byte a byte a oracle_message_hash do Rust v6 — 192 bytes.

    eth_abi.encode(['address','uint256','uint256','uint256','uint256','address'],
                   [user, chain_id, amount, risk, nonce, contract])
    O Rust concatena pad32(user) || chain_id || amount || risk || nonce || pad32(contract)
    — resultado identico (provado no teste cross-language).
    """
    return Web3.keccak(
        encode(
            ["address", "uint256", "uint256", "uint256", "uint256", "address"],
            [user_address, chain_id, amount, risk_score, nonce, contract],
        )
    )


def oracle_nonce_key(user_address: str, nonce: int) -> bytes:
    """Espelha oracle_nonce_key do Rust — chave de anti-replay on-chain."""
    user20 = bytes.fromhex(Web3.to_checksum_address(user_address)[2:])
    return Web3.keccak(user20 + nonce.to_bytes(32, "big"))


def sign_hash_compat(message_hash, private_key):
    """Assina um hash cru (keccak) — API de acordo com a versao do eth-account."""
    fn = (
        getattr(Account, "unsafe_sign_hash", None)
        or getattr(Account, "_sign_hash", None)
        or getattr(Account, "signHash")
    )
    return fn(message_hash, private_key)


def calculate_risk(feats: np.ndarray) -> dict:
    """Motor REAL v6 — argmin deterministico sobre as 8 features lidas da chain.

    O argmin_classify do honesty_experiment.py e o classificador de producao;
    o QCSNRiskEngine.classify (Gibbs exata, equivalente ao quench) serve de
    INTEGRIDADE: se os dois divergirem, o servico recusa assinar (fail-closed).

    [DEFESA ADVERSARIA]: score na faixa 59.x% (mimetizando o limite) e empurrado
    para a zona de bloqueio — o invasor nao pode raspar em 59,99%.
    """
    name = argmin_classify(feats, _PROFILES, _NAMES)
    name2, _verdict, p_star, _E = _ENGINE.classify(feats)
    if name != name2:
        raise RuntimeError(  # fail-closed: assinatura de estado inconsistente nao sai
            f"INTEGRIDADE VIOLADA: argmin={name} != gibbs={name2} — recusando assinar"
        )

    risk = verdict_to_risk_x100(name, p_star)
    if 5900 <= risk < LIMITE_RISCO:
        risk += 150  # zona de raspagem de limite -> bloqueio seguro

    return {
        "name": name,
        "qcsn_verdict": RISK_OF[name],
        "risk_x100": risk,
        "p_star": float(p_star),
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "threshold": THRESHOLD,
            "oracles": [a.address for a in _ORACLE_KEYS],
            "chain_id": CHAIN_ID,
            "contract": CONTRACT_ADDRESS,
            "rpc": RPC_URL,
            "motor": "argmin deterministico (honesty_experiment) sobre features reais (RPC)",
        }
    )


@app.route("/score", methods=["POST"])
def get_score():
    data = request.get_json(silent=True) or {}

    user_address = Web3.to_checksum_address(
        data.get("user", "0x0000000000000000000000000000000000000000")
    )
    amount = int(data.get("amount", 0))
    nonce = int(data.get("nonce", 0))
    to = data.get("to", user_address)
    calldata = data.get("data", "0x")
    value = int(data.get("value", amount or 0))
    token = data.get("token") or None

    if not CONTRACT_ADDRESS:
        return jsonify({"error": "ZEUS_CONTRACT_ADDRESS nao configurado no .env"}), 503

    # 1) features lidas do estado REAL da chain (sem stub, sem vetor inventado)
    feats, _origins = extract_features(RPC_URL, user_address, to, calldata, value, token, verbose=False)

    # 2) argmin deterministico do honesty_experiment + checagem de integridade Gibbs
    result = calculate_risk(feats)
    risk_score = result["risk_x100"]

    # 3) domain separation v6: chain_id + contrato entram no hash assinado
    msg_hash = oracle_message_hash(user_address, CHAIN_ID, CONTRACT_ADDRESS, amount, risk_score, nonce)

    # 4) MULTISIG: assina com 2+ chaves distintas — o contrato exige threshold 2
    signatures = [
        bytes(sign_hash_compat(msg_hash, k.key).signature).hex() for k in _ORACLE_KEYS[:3]
    ]

    return jsonify(
        {
            "score": risk_score,
            "name": result["name"],
            "qcsn_verdict": result["qcsn_verdict"],
            "p_star": result["p_star"],
            "verdict": "BLOQUEAR" if risk_score >= LIMITE_RISCO else "LIBERAR",
            "signatures": signatures,
            "signature": signatures[0],  # compatibilidade com a extensao (v5)
            "oracles": [a.address for a in _ORACLE_KEYS[:3]],
            "oracle": _ORACLE_KEYS[0].address,
            "chain_id": CHAIN_ID,
            "contract": CONTRACT_ADDRESS,
        }
    )


if __name__ == "__main__":
    # producao: sem debug (evita vazamento de logs/stack com dados sensíveis)
    app.run(port=8080, debug=False)
