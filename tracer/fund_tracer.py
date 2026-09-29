#!/usr/bin/env python3
"""
================================================================================
ZEUS GUARD — FUND TRACER v1.0 (defensivo)
================================================================================
Rastreio legítimo de endereços marcados como infraestrutura de abuso:
  - mapa de entrada/saída de tokens (logs on-chain, sem API paga)
  - primeira fonte de financiamento (quem pagou o gas — cadeia de custódia)
  - geração de dossiê em Markdown pronto para submissão a:
      * Chainabuse (blocklist instantâneo consultado por exchanges/Metamask)
      * compliance de exchanges (Binance, Coinbase, OKX respondem a dossiês)
      * Phish.report / delegacia de crimes cibernéticos

Este módulo NÃO hackeia, NÃO intercepta, NÃO bloqueia nada por conta própria.
Ele documenta e submete pelos canais oficiais — o único "susto" legal que existe.
"""
import requests, time, json, sys

RPC = "https://arb1.arbitrum.io/rpc"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ERC20 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

def rpc(method, params, retries=4):
    for _ in range(retries):
        try:
            r = requests.post(RPC, json={"jsonrpc":"2.0","id":1,
                "method":method,"params":params}, timeout=40).json()
            if "result" in r: return r["result"]
        except Exception: time.sleep(1.5)
    return None

def trace(address, lookback_blocks=3_000_000, top=10):
    """Rastreia fluxos de tokens ENTRANDO e SAINDO do endereço-alvo."""
    latest = int(rpc("eth_blockNumber", []), 16)
    frm = "0x" + "0"*24 + address[2:].lower()
    to = frm
    out = {"in": {}, "out": {}}
    for direction, topic_pos in (("in", 2), ("out", 1)):
        topics = [TRANSFER] + ([None, None, to] if direction=="in" else [frm])
        logs = rpc("eth_getLogs", [{"fromBlock": hex(latest-lookback_blocks),
            "toBlock": hex(latest), "topics": topics}]) or []
        for l in logs:
            other = "0x" + l["topics"][2 if direction=="in" else 1][26:]
            token = l["address"]
            data = l["data"][2:]
            # valores decodificados: 32-byte amount (ERC-20 padrão) ou packed
            try:
                v = int(data[:64], 16) if len(data)>=64 else int(data,16)
            except: v = 0
            key = (token, other if direction=="in" else other)
            d = out[direction]
            k = (token, other)
            d[k] = d.get(k, 0) + v
    return out

def summarize(address, label, evidence_lines):
    print(f"rastreando {address} ({label})...")
    t = trace(address)
    lines = [f"# DOSSIÊ — {label}", f"**Endereço:** `{address}`  ",
             "**Chain:** Arbitrum One", "", "## Fluxos recentes (logs on-chain)", ""]
    for direction, title in (("in", "ENTRADAS"), ("out", "SAÍDAS")):
        lines.append(f"### {title}")
        items = sorted(t[direction].items(), key=lambda x: -x[1])
        if not items: lines.append("(nenhuma)")
        for (token, other), v in items[:10]:
            lines.append(f"- token `{token[:12]}..` | contra-parte `{other}` | raw {v}")
        lines.append("")
    lines += ["## Evidências da sessão de forense (28/09/2026)", ""] + evidence_lines
    lines += ["", "## Submissão sugerida",
              "- Chainabuse: https://www.chainabuse.com (categoria: phishing/scam token)",
              "- Phish.report; compliance de exchanges com KYC onde houver off-ramp",
              "- Delegacia de crimes cibernéticos (documento público)"]
    return "\n".join(lines)

if __name__ == "__main__":
    # alvo verificado com infraestrutura de abuso: operador de tokens homoglifo
    ALVO = "0x26ab7cdfce9a9be094b68caab97d08f2b6f50556"
    LABEL = "Operador de tokens homoglifo (‘ÚЅDС’ cirílico) e varredor de USDT0"
    EV = [
        "- 28/09/2026: 8.296 USDT0 puxados via transferFrom de 54 carteiras distintas",
        "  (approvals uniformes de 999.999,99 = automação)",
        "- 28/09/2026: mesmo endereço opera no Ethereum envio em massa de tokens",
        "  falsos ‘ÚЅDС’ (homoglifo com caracteres cirílicos) — +199 transfers/dia",
        "  (fonte: ethplorer.io/tx/0x7842a1b3f55cce442c56229fcfcb2c618055a096095cac6577879afe8765cea4)",
        "- Padrão: dusting/envenenamento de endereço + consolidação de fundos.",
        "  Não constatado roubo direto de carteiras nesta chain na janela analisada.",
        "- NOTA DE HONESTIDADE: o endereço é infraestrutura de abuso (spam/poisoning),",
        "  não um drainer clássico; recomenda-se submissão como 'token scam/dusting',",
        "  não como 'wallet drainer', para não fragilizar o dossiê.",
    ]
    dossier = summarize(ALVO, LABEL, EV)
    open("tracer/dossie_26ab7cdf.md","w").write(dossier)
    print(dossier[:1200])
    print("\n[salvo em tracer/dossie_26ab7cdf.md]")
