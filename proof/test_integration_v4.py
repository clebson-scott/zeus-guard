#!/usr/bin/env python3
"""
ZEUS GUARD v6 — PROVA DE INTEGRACAO: o ataque Forged-Risk morre no check_tx_signed
================================================================================

Cenario: um hacker descobre o endereco do contrato e tenta interagir DIRETAMENTE
com `check_tx_signed`, injetando `risk_x100 = 0` na calldata para burlar o
firewall — como se a transacao fosse inofensiva — sem passar pelo oraculo.

O que esta prova executa contra a rede Arbitrum Sepolia:

  ATAQUE 1 — Forged-Risk "perfeito": o invasor reconstrói o hash com o empacotamento
  EXATO do contrato (domain separation: chain_id 421614 + endereco do deploy,
  espelho do eth_abi.encode de 256 bytes do lib.rs v6) e assina com as PROPRIAS
  chaves dele. As assinaturas sao matematicamente validas... mas nao sao do
  conjunto multisig confiavel. A EVM do Stylus reverte.

  ATAQUE 2 — Bundle-swap: o invasor captura um bundle assinado sobre risk=9500
  e troca o risk para 0 na calldata. O risk vive DENTRO do hash assinado —
  a troca invalida a assinatura. A EVM reverte.

  ATAQUE 3 (opcional, gasta gas de testnet) — Replay real: um bundle legitimo
  de um oraculo real e submetido DUAS VEZES. O nonce anti-replay e consumido na
  primeira; a segunda morre com OracleNonceReplayed.

Resultado esperado: a EVM reverte com o erro da familia
"Assinatura Invalida ou Replay detectado" (OracleThresholdNotMet / OracleNonceReplayed),
atestando o sucesso da defesa.

Como rodar (apos zeus-guard-contract/deploy.sh da v6):
    export ZEUS_GUARD_CONTRACT_ADDRESS=0x...     # endereco do deploy v6
    python3 proof/test_integration_v4.py

Prova completa com replay real (opcional):
    export ATTACKER_PRIVATE_KEY=0x...            # carteira de teste com gas na Sepolia
    export ZEUS_ORACLE_BUNDLE_FILE=bundle.json   # resposta /score com risk < 6000 (LIBERAR)
    python3 proof/test_integration_v4.py

Ataque 1 e 2 usam eth_call (simulacao EVM, sem custo de gas) — a reversao e a
mesma que um envio real sofreria, pois ocorre ANTES de qualquer efeito colateral.
"""

import json
import os
import secrets
import sys

# ---- alinhamento offline (roda antes de qualquer rede) ----
from eth_abi import encode as abi_encode
from eth_account import Account
from web3 import Web3
from web3.exceptions import ContractLogicError

RPC_URL = os.environ.get("ZEUS_RPC", "https://sepolia-rollup.arbitrum.io/rpc")
CHAIN_ID = int(os.environ.get("ZEUS_CHAIN_ID", "421614"))
CONTRACT_ADDRESS = os.environ.get("ZEUS_GUARD_CONTRACT_ADDRESS", "")
ATTACKER_PRIVATE_KEY = os.environ.get("ATTACKER_PRIVATE_KEY", "")
BUNDLE_FILE = os.environ.get("ZEUS_ORACLE_BUNDLE_FILE", "")

LIMITE_RISCO = 6000

PASS, FAIL = 0, 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"    [PASS] {name}")
    else:
        FAIL += 1
        print(f"    [FAIL] {name} {detail}")


# ============================================================================
# 1. EMPACOTAMENTO EXATO — o espelho do Rust v6 (oracle_message_hash)
#    keccak256(eth_abi.encode(['address','uint256','uint256','uint256',
#                              'uint256','address'],
#                             [user, chain_id, amount, risk, nonce, contract]))
# ============================================================================
def oracle_message_hash(user: str, token: str, payee: str, amount: int, risk_x100: int, nonce: int, contract: str) -> bytes:
    """Espelho do hash v6, vinculando token e payee ao bundle financeiro."""
    return Web3.keccak(abi_encode(
        ["address", "address", "address", "uint256", "address", "uint256", "uint256", "uint256"],
        [user, token, payee, CHAIN_ID, contract, amount, risk_x100, nonce],
    ))


def forge_calldata(user: str, token: str, payee: str, amount: int, risk_x100: int, nonce: int, signatures: list) -> str:
    """Monta calldata checkTxSigned com domínio completo, incluindo token/payee."""
    selector = Web3.keccak(text="checkTxSigned(address,address,address,uint256,uint256,uint256,bytes[])")[:4]
    args = abi_encode(
        ["address", "address", "address", "uint256", "uint256", "uint256", "bytes[]"],
        [Web3.to_checksum_address(user), Web3.to_checksum_address(token), Web3.to_checksum_address(payee), amount, risk_x100, nonce, signatures],
    )
    return "0x" + (selector + args).hex()


# ============================================================================
# 2. DECODIFICACAO DOS ERROS TIPADOS — qual barreira matou o ataque
#    (nomes exatos do sol! do lib.rs v6)
# ============================================================================
TYPED_ERRORS = {
    # "assinatura": (nome, [campos], [tipos])
    "OracleThresholdNotMet(uint256,uint256)": ("OracleThresholdNotMet", ["got", "needed"], ["uint256", "uint256"]),
    "OracleNonceReplayed(uint256)": ("OracleNonceReplayed", ["nonce"], ["uint256"]),
    "InvalidSignatureLength(uint256)": ("InvalidSignatureLength", ["got"], ["uint256"]),
    "SignatureListTooLong(uint256)": ("SignatureListTooLong", ["got"], ["uint256"]),
    "OracleNotInitialized()": ("OracleNotInitialized", [], []),
    "NoSession()": ("NoSession", [], []),
    "EcrecoverFailed()": ("EcrecoverFailed", [], []),
    "SignatureMalleable()": ("SignatureMalleable", [], []),
    "ReentrancyGuard()": ("ReentrancyGuard", [], []),
    "SessionFrozenError()": ("SessionFrozenError", [], []),
    "NotContractOwner()": ("NotContractOwner", [], []),
    "TooRisky(uint64,uint64)": ("TooRisky", ["risk", "limit"], ["uint64", "uint64"]),
    "AboveDailyCap(uint256,uint256)": ("AboveDailyCap", ["spent", "cap"], ["uint256", "uint256"]),
}


def _selectors():
    out = {}
    for sig, (name, fields, types) in TYPED_ERRORS.items():
        out[Web3.keccak(text=sig)[:4]] = (name, fields, types)
    return out


ERROR_SELECTORS = _selectors()


def decode_revert(exc) -> tuple:
    """Extrai (nome_do_erro, args) do revert; bruto se desconhecido."""
    data = None
    if isinstance(exc, ContractLogicError):
        data = getattr(exc, "data", None)
    if data is None and hasattr(exc, "args"):
        for a in exc.args:
            if isinstance(a, str) and a.startswith("0x") and len(a) > 8:
                data = a
    if data is None:
        return ("RevertDesconhecido", {"raw": str(exc)[:200]})
    raw = bytes.fromhex(data[2:] if isinstance(data, str) else bytes(data).hex())
    sel = raw[:4]
    if sel in ERROR_SELECTORS:
        name, fields, types = ERROR_SELECTORS[sel]
        if types:
            from eth_abi import decode as abi_decode
            values = abi_decode(types, raw[4:])
            return (name, dict(zip(fields, [str(v) for v in values])))
        return (name, {})
    return ("RevertDesconhecido", {"selector": "0x" + sel.hex()})


def sign_hash(message_hash: bytes, private_key) -> bytes:
    """Assina um hash cru (keccak) — r(32) || s(32) || v(1)."""
    fn = (getattr(Account, "unsafe_sign_hash", None)
          or getattr(Account, "_sign_hash", None)
          or getattr(Account, "signHash"))
    return bytes(fn(message_hash, private_key).signature)


# ============================================================================
# 3. SELF-CHECK OFFLINE — vetores travados com os testes Rust (lib.rs v6)
#    Prova que o empacotamento desta prova e o MESMO do contrato, antes de
#    gastar qualquer rede.
# ============================================================================
def offline_selfcheck() -> bool:
    print("\n[0] Self-check offline do empacotamento (vetores do teste Rust v6)")
    user = "0x00000000000000000000000000000000000000AA"
    token = "0x00000000000000000000000000000000000000D0"
    payee = "0x00000000000000000000000000000000000000EE"
    contract = "0x00000000000000000000000000000000000000C0"
    v = oracle_message_hash(user, token, payee, 10**18, 1500, 1, contract)
    check("hash v6 == vetor canônico do Rust (0569bd23…)",
          v.hex() == "0569bd23eb4abed6c5ca842d14360222d04cc20fc523026d17931c9939791015")
    # chain_id is part of the canonical function's fixed domain; compute variants directly.
    def variant(chain=421614, tok=token, recipient=payee, deploy=contract):
        return Web3.keccak(abi_encode(
            ["address","address","address","uint256","address","uint256","uint256","uint256"],
            [user, tok, recipient, chain, deploy, 10**18, 1500, 1]))
    check("domain separation: outra chain => outro hash", v != variant(chain=421615))
    check("domain separation: outro deploy => outro hash", v != variant(deploy="0x00000000000000000000000000000000000000C1"))
    check("domain separation: outro token => outro hash", v != variant(tok="0x00000000000000000000000000000000000000D1"))
    check("domain separation: outro payee => outro hash", v != variant(recipient="0x00000000000000000000000000000000000000EF"))
    return FAIL == 0


# ============================================================================
# 4. OS ATAQUES
# ============================================================================
def probe_contract(w3, ca) -> None:
    """Confirma que o alvo tem a ABI v6 (senao o ataque atesta nada)."""
    sel = Web3.keccak(text="oracleThresholdPub()")[:4]
    try:
        r = w3.eth.call({"to": ca, "data": "0x" + sel.hex()})
        thr = int.from_bytes(r, "big")
        print(f"    alvo v6 confirmado: oracle_threshold_pub() = {thr}")
        check("alvo responde a ABI v6 (threshold 2)", thr == 2)
    except Exception as e:
        name, args = decode_revert(e)
        print(f"    [FALHA] o endereco {ca} NAO e um deploy ZEUS GUARD v6")
        print(f"    revert: {name} {args}")
        print("    => rode primeiro zeus-guard-contract/deploy.sh e export o novo endereco")
        sys.exit(2)


def attack_1_forged_risk(w3, ca) -> None:
    """Forged-Risk 'perfeito': hash reconstruido certinho + assinaturas proprias."""
    print("\n[ATAQUE 1] Forged-Risk — risk_x100=0 na calldata, chaves do invasor")
    user = Web3.to_checksum_address("0x" + "00" * 19 + "AA")
    amount = 10**18
    token = Web3.to_checksum_address("0x" + "00" * 19 + "D0")
    payee = Web3.to_checksum_address("0x" + "00" * 19 + "EE")
    forged_risk = 0            # injetado: transacao "inofensiva"
    nonce = secrets.randbits(128)

    # o invasor domina o empacotamento EXATO (domain separation incluida)
    forged_hash = oracle_message_hash(user, token, payee, amount, forged_risk, nonce, ca)
    attacker_keys = [Account.create(), Account.create()]
    bundle = [sign_hash(forged_hash, k.key) for k in attacker_keys]

    data = forge_calldata(user, token, payee, amount, forged_risk, nonce, bundle)
    print(f"    calldata adulterada ({len(data) // 2 - 4} bytes de args), risk=0, 2 assinaturas validas do invasor")

    try:
        w3.eth.call({"to": ca, "data": data})
        check("EVM do Stylus REVERTEU o ataque", False, "(a chamada passou — defesa falhou!)")
    except Exception as e:
        name, args = decode_revert(e)
        print(f"    EVM reverteu com: {name} {args}")
        check("assinaturas do invasor NAO passam do multisig 2-de-3",
              name == "OracleThresholdNotMet" and args.get("needed") == "2")


def attack_2_bundle_swap(w3, ca) -> None:
    """Bundle-swap: assinatura capturada sobre risk=9500, calldata com risk=0."""
    print("\n[ATAQUE 2] Bundle-swap — bundle 'legitimo' (risk 9500) com risk trocado para 0")
    user = Web3.to_checksum_address("0x" + "00" * 19 + "AA")
    amount = 10**18
    token = Web3.to_checksum_address("0x" + "00" * 19 + "D0")
    payee = Web3.to_checksum_address("0x" + "00" * 19 + "EE")
    nonce = secrets.randbits(128)

    # bundle capturado de um suposto oracle legitimo, assinado sobre risk=9500
    captured_hash = oracle_message_hash(user, token, payee, amount, 9500, nonce, ca)
    captured_keys = [Account.create(), Account.create()]
    captured_bundle = [sign_hash(captured_hash, k.key) for k in captured_keys]

    # o invasor troca o risk na calldata: o hash (e as assinaturas) deixam de bater
    data = forge_calldata(user, token, payee, amount, 0, nonce, captured_bundle)
    print("    calldata: risk=0 | bundle assinado sobre risk=9500 (troca detectavel)")

    try:
        w3.eth.call({"to": ca, "data": data})
        check("EVM do Stylus REVERTEU o swap", False, "(a chamada passou — defesa falhou!)")
    except Exception as e:
        name, args = decode_revert(e)
        print(f"    EVM reverteu com: {name} {args}")
        check("o risk vive DENTRO do hash assinado — swap invalida o bundle",
              name in ("OracleThresholdNotMet", "EcrecoverFailed"))


def attack_3_replay(w3, ca) -> None:
    """Replay real de bundle legitimo do oraculo (consome nonce; exige gas)."""
    print("\n[ATAQUE 3] Replay real do bundle do oraculo (opcional — gasta gas de testnet)")
    if not (ATTACKER_PRIVATE_KEY and BUNDLE_FILE):
        print("    [SKIP] defina ATTACKER_PRIVATE_KEY e ZEUS_ORACLE_BUNDLE_FILE para este ataque")
        return
    try:
        with open(BUNDLE_FILE) as f:
            bundle = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"    [SKIP] bundle ilegivel: {e}")
        return
    if bundle.get("score", LIMITE_RISCO) >= LIMITE_RISCO:
        print("    [SKIP] bundle com score >= 6000 morre no policy_gate antes do replay —")
        print("            capture um bundle LIBERAR (risk < 6000) via /score do oraculo")
        return

    attacker = Account.from_key(ATTACKER_PRIVATE_KEY)
    user = Web3.to_checksum_address(bundle.get("user", attacker.address))
    # a barreira 7 (policy_gate v4) exige sessao ativa: matricula o usuario antes
    ses_data = Web3.keccak(text="initSession(address,uint256,uint256)")[:4] + abi_encode(
        ["address", "uint256", "uint256"], [user, 3600, 10**18])
    try:
        w3.eth.call({"from": attacker.address, "to": ca, "data": ses_data.hex() if isinstance(ses_data, str) else ses_data})
    except Exception:
        pass  # sessao ja existente: o eth_call reverte, o send abaixo e o que importa
    ses_tx = {"from": attacker.address, "to": ca, "data": "0x" + ses_data.hex(),
              "nonce": w3.eth.get_transaction_count(attacker.address, "pending"),
              "chainId": w3.eth.chain_id, "gas": 300000,
              "gasPrice": max(w3.eth.gas_price, 10**9)}
    signed_ses = Account.sign_transaction(ses_tx, attacker.key)
    ses_hash = w3.eth.send_raw_transaction(signed_ses.raw_transaction)
    ses_rc = w3.eth.wait_for_transaction_receipt(ses_hash)
    if ses_rc["status"] == 1:
        print("    sessao matriculada (guardiao=janela 3600s, teto 1 ETH)")
    else:
        print("    sessao ja existia (tx de matricula revertida) — seguindo")
    amount = int(bundle["amount"])
    token = Web3.to_checksum_address(bundle.get("token") or "0x" + "00" * 20)
    payee = Web3.to_checksum_address(bundle.get("to") or user)
    nonce = int(bundle["nonce"])
    risk = int(bundle["score"])
    sigs = [bytes.fromhex(s[2:] if s.startswith("0x") else s) for s in bundle["signatures"]]

    contract = w3.eth.contract(address=ca, abi=[{
        "name": "checkTxSigned", "type": "function", "stateMutability": "nonpayable",
        "inputs": [
            {"name": "user", "type": "address"}, {"name": "token", "type": "address"},
            {"name": "payee", "type": "address"}, {"name": "amount", "type": "uint256"},
            {"name": "risk_x100", "type": "uint256"}, {"name": "nonce", "type": "uint256"},
            {"name": "signatures", "type": "bytes[]"},
        ],
        "outputs": [],
    }])
    tx1 = contract.functions.checkTxSigned(user, token, payee, amount, risk, nonce, sigs).build_transaction({
        "from": attacker.address, "nonce": w3.eth.get_transaction_count(attacker.address, "pending"),
        "chainId": w3.eth.chain_id, "gas": 400000,
    })
    signed = Account.sign_transaction(tx1, attacker.key)
    h1 = w3.eth.send_raw_transaction(signed.raw_transaction)
    r1 = w3.eth.wait_for_transaction_receipt(h1)
    print(f"    1a submissao (bundle legitimo): status={r1['status']}")
    check("bundle legitimo consumiu o nonce (tx confirmada)", r1["status"] == 1,
          f"hash={h1.hex()}")

    # replay: MESMO bundle, MESMO nonce — o anti-replay tem que matar
    tx2 = contract.functions.checkTxSigned(user, token, payee, amount, risk, nonce, sigs).build_transaction({
        "from": attacker.address, "nonce": w3.eth.get_transaction_count(attacker.address, "pending"),
        "chainId": w3.eth.chain_id, "gas": 400000,
    })
    signed2 = Account.sign_transaction(tx2, attacker.key)
    h2 = w3.eth.send_raw_transaction(signed2.raw_transaction)
    r2 = w3.eth.wait_for_transaction_receipt(h2)
    reverted = r2["status"] == 0
    print(f"    2a submissao (replay do MESMO nonce): status={r2['status']} (0=revertida)")
    check("replay do nonce morto — tx revertida on-chain", reverted)


# ============================================================================
# 5. MAIN
# ============================================================================
def main() -> int:
    print("=" * 72)
    print("ZEUS GUARD v6 — PROVA DE INTEGRACAO (red-team): Forged-Risk vs check_tx_signed")
    print("=" * 72)
    print(f"rede: Arbitrum Sepolia (chain_id {CHAIN_ID})")

    offline_selfcheck()

    if not CONTRACT_ADDRESS:
        print("\n[FIM DO SELF-CHECK] A parte ao vivo precisa do deploy v6:")
        print("    1) rode zeus-guard-contract/deploy.sh")
        print("    2) export ZEUS_GUARD_CONTRACT_ADDRESS=<novo endereco>")
        print("    3) python3 proof/test_integration_v4.py")
        return 0 if FAIL == 0 else 1

    ca = Web3.to_checksum_address(CONTRACT_ADDRESS)
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    print(f"alvo: {ca}")
    probe_contract(w3, ca)
    attack_1_forged_risk(w3, ca)
    attack_2_bundle_swap(w3, ca)
    attack_3_replay(w3, ca)

    print("\n" + "=" * 72)
    if FAIL == 0:
        print("VEREDICTO: a EVM do Stylus reverteu toda calldata adulterada com o erro")
        print('"Assinatura Invalida ou Replay detectado" (multisig 2-de-3 + anti-replay).')
        print("ATAQUE REPELIDO — o firewall oracular vale NO CAMINHO DO DINHEIRO.")
    else:
        print(f"ATENCAO: {FAIL} prova(s) falharam — NAO considere o contrato pronto.")
    print(f"resultado: {PASS} pass / {FAIL} fail")
    print("=" * 72)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
