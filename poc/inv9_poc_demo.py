#!/usr/bin/env python3
"""
=====================================================================
PoC SEGURA (red-team) — Receiver-Phishing via LI.FI API + Detector INV9
=====================================================================
PROVA DE CONCEITO DE CARÁTER ESTRITAMENTE DEFENSIVO:
- NÃO assina transação nenhuma (não há chaves neste script)
- NÃO transmite nada pra blockchain (sem broadcast)
- Usa ENDEREÇOS DE PLACEHOLDER conhecidos, não vítimas
- Demonstra: (1) o golpe; (2) o detector que o mata (INV9)

O que este PoC prova:
1. A API pública da LI.FI (li.quest/v1/quote) monta uma transação de
   bridge OFICIAL com QUALQUER endereço no parâmetro `receiver` —
   inclusive um diferente de `fromAddress`. Isso é o mecanismo exato
   do golpe "Axioraswap": site falso + receiver = carteira do golpista.
2. O campo receiver embarca no calldata da transação ANTES da assinatura
   — logo, é interceptável no momento da confirmação da carteira.
3. O detector INV9 (receiver-match) discrimina 100% os dois casos:
   bridge legítimo (receiver == carteira conectada) LIBERA
   bridge de golpe (receiver != carteira conectada) BLOQUEIA.
"""
import requests, json, sys

API = "https://li.quest/v1/quote"

# --- Endereços de placeholder (públicos, documentais, não são vítimas) ---
ALICE_DOC_ADDR = "0xd8da611269cbcbbe37eb56af4dd5ac1e260b90a3"  # endereço público conhecido (placeholder "vítima")
BOB_DEMO_ADDR  = "0xDeaDBeef00000000000000000000000000000000"  # dummy clássico (placeholder "golpista")

USDC_ARBITRUM = "0xaf88d065e77c8cc2239327c5edb3a432268e5831"
USDC_BASE     = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

def get_quote(receiver, label):
    """Chama a API pública da LI.FI exatamente como o frontend legítimo
    (ou o site falso) faria. Única diferença entre os dois: o `receiver`."""
    params = {
        "fromChain": 42161,          # Arbitrum
        "toChain": 8453,             # Base
        "fromToken": USDC_ARBITRUM,
        "toToken": USDC_BASE,
        "fromAmount": 300000000,     # 300 USDC (6 decimais)
        "fromAddress": ALICE_DOC_ADDR,
        "receiver": receiver,        # <<< o campo inteiro do golpe
    }
    r = requests.get(API, params=params, timeout=30)
    if r.status_code != 200:
        print(f"[{label}] API retornou {r.status_code}: {r.text[:200]}")
        return None
    return r.json()

def extract_receiver_from_calldata(data_hex):
    """Prova forense: o receiver embarca no calldata.
    Varre endereços de 20 bytes no calldata devolvido pela API."""
    body = data_hex[2:] if data_hex.startswith("0x") else data_hex
    found = []
    for i in range(0, len(body) - 40 + 1):
        seg = body[i:i+40]
        if seg[:24] == "0"*24:
            try: v = int(seg, 16)
            except: continue
            # filtro de entropia: endereco real tem bytes altos nao-nulos
            # (descarta inteiros pequenos como offsets/tamanhos ABI)
            if v >= 2**128 and v < 2**160:
                found.append(("0x"+seg[24:]).lower())
    return sorted(set(found))

def inv9_check(from_addr, receiver, calldata_addrs):
    """INV9 — receiver-match: o detector proposto pro ZEUS GUARD.
    Compara o receiver do bridge com a carteira conectada (fromAddress)."""
    fr = from_addr.lower()
    rc = receiver.lower()
    if rc == fr:
        return "LIBERAR", "receiver == carteira conectada (bridge legítimo)"
    in_cd = rc in [a for a in calldata_addrs]
    return ("BLOQUEAR",
            f"receiver {rc[:14]}.. != carteira conectada {fr[:14]}.. "
            f"| receiver presente no calldata: {in_cd} → ASSINATURA DE PHISHING")

def run_case(receiver, label):
    print(f"\n{'='*68}\nCASO: {label}\n{'='*68}")
    q = get_quote(receiver, label)
    if not q:
        return
    tx = q.get("transactionRequest") or {}
    to = tx.get("to", "?")
    data = tx.get("data", "0x")
    gas = tx.get("gasLimit", "?")
    print(f"API respondeu cotação REAL: {q.get('estimate',{}).get('fromAmount')} "
          f"USDC → {q.get('estimate',{}).get('toAmount', '?')} USDC na Base")
    print(f"transação NÃO-ASSINADA gerada pela API:")
    print(f"  to:   {to}   (contrato OFICIAL da LI.FI)")
    print(f"  data: {data[:70]}...({len(data)//2-1} bytes)")
    print(f"  gas:  {gas}")
    # prova forense: receiver dentro do calldata
    addrs = extract_receiver_from_calldata(data)
    print(f"endereços embutidos no calldata: {len(addrs)}")
    for a in sorted(set(addrs)):
        tag = ""
        if a == receiver.lower(): tag = "  ← RECEIVER (destino do dinheiro)"
        if a == ALICE_DOC_ADDR.lower(): tag = "  ← remetente (vítima)"
        if a == USDC_ARBITRUM.lower(): tag = "  ← token USDC"
        if a == to.lower(): tag = "  ← contrato LI.FI (executor)"
        print(f"    {a}{tag}")
    # o detector
    verdict, why = inv9_check(ALICE_DOC_ADDR, receiver, addrs)
    print(f"\nZEUS GUARD / INV9: [{verdict}]")
    print(f"  motivo: {why}")
    return verdict

if __name__ == "__main__":
    print("="*68)
    print("PoC SEGURA — nada é assinado, nada é transmitido à chain.")
    print("Endereços: placeholder públicos (0xd8da... / 0x...dEaD).")
    print("="*68)
    # CENÁRIO A — bridge legítimo (como o Jumper real faz)
    v_a = run_case(ALICE_DOC_ADDR, "A) BRIDGE LEGÍTIMO — receiver == carteira conectada")
    # CENÁRIO B — o golpe (como o site falso faz): mesma chamada, receiver trocado
    v_b = run_case(BOB_DEMO_ADDR, "B) O GOLPE — receiver == carteira do 'golpista' (placeholder)")
    print("\n" + "="*68)
    print("RESUMO DA PROVA:")
    print(f"  cenário A (legítimo): INV9 = {v_a}")
    print(f"  cenário B (golpe):    INV9 = {v_b}")
    if v_a == "LIBERAR" and v_b == "BLOQUEAR":
        print("\n  ✔ PROVA COMPLETA: mesma API, mesma infraestrutura legítima,")
        print("    único delta = campo receiver. INV9 separa os dois casos 100%.")
    print("  (Nenhuma transação foi assinada ou enviada. Sem chaves. Sem vítimas.)")
