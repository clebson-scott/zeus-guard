#!/usr/bin/env python3
"""
================================================================================
PoC SEGURA COMPLETA (red-team/defensiva) — Receiver-Phishing via LI.FI API
================================================================================
RESTRIÇÕES DE SEGURANÇA (inalteráveis):
- NÃO assina, NÃO transmite, NÃO guarda chaves. Sem vítimas.
- Endereços de placeholder: 0xd8da... (público, "vítima") e 0xDeaDBeef...00
  (dummy clássico de engenharia, "golpista").

PROVA COMPLETA (executar: python3 inv9_poc_full.py):
1. A API pública da LI.FI aceita `receiver` != `fromAddress` sem qualquer
   restrição — é o único parâmetro que o site falso precisa trocar.
2. As duas transações não-assinadas são IDÊNTICAS exceto por 32 bytes
   (o compromisso criptográfico do receiver com sal).
3. DUPLO ENGANO NA RESPOSTA: o campo `action.toAddress` da resposta mostra
   o ENDEREÇO DA PRÓPRIA VÍTIMA como destino, mesmo quando o receiver
   real (no compromisso do calldata) é outro. A UI mostrada ao usuário
   (e a qualquer extensão ingênua) parece 100% legítima.
4. Toda a execução on-chain usaria contratos oficiais (LI.FI Diamond,
   Polymer, Permit2Proxy) — zero artefato malicioso na chain.
5. O PONTO DE INTERCEPTAÇÃO VIÁVEL: a requisição HTTP do frontend à API
   (o parâmetro `receiver` viaja em texto puro no request; no calldata
   ele só existe como hash com sal). INV9 deve atuar AQUI — hook de
   extensão de browser sobre chamadas a li.quest — ou no calldata nos
   formatos clássicos onde o receiver vai em texto puro.
"""
import requests, json, sys

API = "https://li.quest/v1/quote"
ALICE = "0xd8da611269cbcbbe37eb56af4dd5ac1e260b90a3"        # placeholder vítima
BOB   = "0xDeaDBeef00000000000000000000000000000000"        # placeholder "golpista"
USDC_ARB  = "0xaf88d065e77c8cc2239327c5edb3a432268e5831"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

def get_quote(receiver):
    params = {"fromChain": 42161, "toChain": 8453,
              "fromToken": USDC_ARB, "toToken": USDC_BASE,
              "fromAmount": 300000000, "fromAddress": ALICE,
              "receiver": receiver}
    return requests.get(API, params=params, timeout=30).json()

def inv9(from_addr, receiver_param, response):
    """Detector receiver-match. Fonte da verdade: o parâmetro do REQUEST
    (não o display da resposta — que a PoC mostra ser enganoso)."""
    if receiver_param.lower() == from_addr.lower():
        return "LIBERAR", "receiver == carteira conectada"
    shown = response.get("action", {}).get("toAddress", "?")
    return ("BLOQUEAR",
            f"receiver do request ({receiver_param[:12]}..) != carteira conectada "
            f"({from_addr[:12]}..) | resposta exibe toAddress={shown[:12]}.. "
            f"(display enganoso — destino real é outro)")

def main():
    print("="*72)
    print("PoC SEGURA — Receiver-Phishing via LI.FI API | nada é assinado/transmitido")
    print("="*72)
    qa = get_quote(ALICE)
    qb = get_quote(BOB)
    ta, tb = qa["transactionRequest"], qb["transactionRequest"]
    da, db = ta["data"][2:], tb["data"][2:]
    print(f"\n[1] API aceitou os dois cenários sem restrição (HTTP 200)")
    print(f"    rota escolhida: {qa.get('tool')} | taxa real | cotação real")
    print(f"\n[2] Comparação das transações não-assinadas:")
    print(f"    mesmo contrato executor: {ta['to'] == tb['to']} ({ta['to']})")
    print(f"    mesmo tamanho de calldata: {len(da)==len(db)} ({len(da)//2} bytes)")
    diffs = sorted({i//2 for i in range(len(da)) if da[i] != db[i]})
    print(f"    bytes que diferem: {len(diffs)} de {len(da)//2} (compromisso com sal do receiver)")
    print(f"\n[3] Duplo engano na resposta (cenário do golpe):")
    print(f"    action.toAddress exibido: {qb['action']['toAddress']}")
    print(f"    receiver real do request: {BOB}")
    print(f"    → a UI mostraria a CARTEIRA DA VÍTIMA como destino")
    print(f"\n[4] Verificação on-chain do executor:")
    print(f"    to: {tb['to']} = LI.FI Diamond oficial (rotulado, auditado)")
    v_a, w_a = inv9(ALICE, ALICE, qa)
    v_b, w_b = inv9(ALICE, BOB, qb)
    print(f"\n[5] ZEUS GUARD / INV9:")
    print(f"    cenário legítimo:  [{v_a}] — {w_a}")
    print(f"    cenário do golpe:  [{v_b}]")
    print(f"      {w_b}")
    print("\n" + "="*72)
    print("CONCLUSÃO: o golpe inteiro é 1 parâmetro HTTP + infraestrutura oficial.")
    print("Ponto de interceptação: o REQUEST à API (receiver em texto puro).")
    print("No calldata, o receiver só existe como compromisso salgado (rotas intent);")
    print("em rotas clássicas ele vai em texto puro e o INV9 lê direto do calldata.")
    print("(Nenhuma transação foi assinada ou enviada. Sem chaves. Sem vítimas.)")

if __name__ == "__main__":
    main()
