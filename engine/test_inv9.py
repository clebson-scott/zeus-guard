#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes INV9 (receiver-match) — executar: python3 test_inv9.py
Cobre: camada request (com display enganoso), camada calldata (formatos
verificados via eth_abi), intents (compromisso salgado → INDETERMINADO),
invariante "sem fonte de verdade não há PASS", robustez contra malformados.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eth_abi import encode as abi_encode
from inv9_receiver_match import (
    inv9_request, inv9_calldata, inv9_evaluate, extract_receiver,
    PASS, ALERT, INDETERMINADO, VERIFIED_DECODERS,
)

ALICE = "0xd8da611269cbcbbe37eb56af4dd5ac1e260b90a3"   # carteira conectada (vítima placeholder)
BOB   = "0xdeadbeef00000000000000000000000000000000"   # receiver do golpista (dummy)
CAROL = "0x145d602b3f7a45f1e4a8ad07ac6db7c8f81bd557"   # terceiro legítimo (placeholder)

DEPOSIT_T = "(address,address,address,address,uint256,uint256,uint256,uint32,uint32,uint32,address,bytes)"
SEL_DV3  = "0x7d0ece9c"
SEL_FILL = "0xc39ffe76"

_failures = []
def check(name, cond, extra=""):
    print(("  [OK]   " if cond else "  [FAIL] ") + name + ("" if cond else "  <- " + extra))
    if not cond:
        _failures.append(name)

def make_depositv3(receiver, depositor=ALICE):
    t = (
        depositor, receiver,
        "0xaf88d065e77c8cc2239327c5edb3a432268e5831",   # inputToken USDC-arb
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",   # outputToken USDC-base
        300_000_000, 299_500_000, 8453, 1727568000, 1727571600, 0,
        "0x0000000000000000000000000000000000000000",
        b"",
    )
    return SEL_DV3 + abi_encode(["(" + ",".join(["address","address","address","address","uint256","uint256","uint256","uint32","uint32","uint32","address","bytes"]) + ")"], [t]).hex()

def make_fillv3relay(receiver, depositor=ALICE):
    t = (
        depositor, receiver,
        "0xaf88d065e77c8cc2239327c5edb3a432268e5831",
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        300_000_000, 299_500_000, 8453, 1727568000, 1727571600, 0,
        "0x0000000000000000000000000000000000000000",
        b"",
    )
    return SEL_FILL + abi_encode(
        ["(" + ",".join(["address","address","address","address","uint256","uint256","uint256","uint32","uint32","uint32","address","bytes"]) + ")", "uint256"],
        [t, 42161]).hex()


def main():
    print("=" * 78)
    print("Testes INV9 — receiver-match | ZEUS GUARD")
    print("=" * 78)

    # ---------- camada 1: request ----------
    print("\n[1] Camada REQUEST (autoritativa)")
    v = inv9_request(ALICE, ALICE)
    check("receiver == conectada → PASS", v.verdict == PASS, v.as_dict())

    v = inv9_request(ALICE, BOB, response_display=ALICE)
    check("receiver != conectada → ALERT", v.verdict == ALERT, v.reason)
    check("display contradiz receiver real → deceptive_display=True", v.deceptive_display is True)
    check("motivo menciona ENGENO ATIVO", "ENGENO ATIVO" in v.reason, v.reason)

    v = inv9_request(ALICE, BOB, response_display=BOB)
    check("display coerente → deceptive_display=False", v.deceptive_display is False)

    v = inv9_request(ALICE, BOB, explicit_confirmation=True)
    check("divergência confirmada explicitamente → PASS registrado", v.verdict == PASS and v.explicit_confirmation)

    v = inv9_request(ALICE, CAROL)
    check("receiver legítimo divergente (ex.: envio a terceiro) sem confirmação → ALERT (não bloqueio)",
          v.verdict == ALERT, v.reason)

    v = inv9_request(ALICE, "0x123")
    check("endereço malformado → INDETERMINADO", v.verdict == INDETERMINADO)

    v = inv9_request(ALICE, "0x" + "g1" * 20)   # g nao e hex
    check("hex inválido → INDETERMINADO, sem exceção", v.verdict == INDETERMINADO)

    v = inv9_request(ALICE, ALICE.upper())
    check("case-insensitive (checksummed) → PASS", v.verdict == PASS)

    # ---------- camada 2: calldata ----------
    print("\n[2] Camada CALLDATA (decodificadores verificados)")
    cd = make_depositv3(ALICE)
    rec, fmt, why = extract_receiver(cd)
    check("depositV3: receiver extraído == ALICE", rec == ALICE, f"{rec} {fmt}")
    v = inv9_calldata(ALICE, cd)
    check("depositV3 receiver==origin → PASS", v.verdict == PASS)

    cd = make_depositv3(BOB)
    rec, fmt, why = extract_receiver(cd)
    check("depositV3: receiver extraído == BOB", rec == BOB, f"{rec}")
    v = inv9_calldata(ALICE, cd)
    check("depositV3 receiver!=origin → ALERT", v.verdict == ALERT, v.reason)
    v = inv9_calldata(ALICE, cd, explicit_confirmation=True)
    check("depositV3 confirmado explicitamente → PASS", v.verdict == PASS and v.explicit_confirmation)

    cd = make_fillv3relay(BOB)
    rec, fmt, why = extract_receiver(cd)
    check("fillV3Relay: receiver extraído == BOB", rec == BOB, f"{rec} {fmt}")
    v = inv9_calldata(ALICE, cd)
    check("fillV3Relay receiver!=origin → ALERT", v.verdict == ALERT)

    cd = make_depositv3(BOB, depositor=CAROL)
    rec, _, _ = extract_receiver(cd)
    check("depositV3 com depositor terceiro: receiver correto (não o depositor)", rec == BOB, rec)

    # ---------- intents: compromisso salgado → INDETERMINADO ----------
    print("\n[3] Intents (receiver = compromisso salgado — evidência empírica LI.FI)")
    fixture = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "inv9_fixture_polymer.json")
    if os.path.exists(fixture):
        poly = json.load(open(fixture))
        cd = poly["calldata"]
        rec, fmt, why = extract_receiver(cd)
        check("polymerCCTP: receiver NÃO extraível (None)", rec is None, f"{rec} {fmt}")
        check("formato identificado como intent-commitment", fmt == "intent-commitment", fmt)
        v = inv9_calldata(ALICE, cd)
        check("intent → INDETERMINADO (nunca adivinha)", v.verdict == INDETERMINADO, v.reason)
        check("motivo aponta para a camada request", "camada request" in v.reason, v.reason)
    else:
        check("fixture polymer presente", False, f"ausente: {fixture}")

    # ---------- invariante: sem fonte de verdade, sem PASS ----------
    print("\n[4] Invariante: sem decodificador verificado NÃO existe PASS")
    cd_unknown = "0xdeadbeef" + "11" * 64
    rec, fmt, why = extract_receiver(cd_unknown)
    check("seletor desconhecido → None", rec is None and fmt == "unknown-selector", fmt)
    v = inv9_calldata(ALICE, cd_unknown)
    check("seletor desconhecido → INDETERMINADO", v.verdict == INDETERMINADO)

    for bad in ["", "0x", "0x1234", "not-hex-zz", "0x" + "zz" * 64]:
        try:
            v = inv9_calldata(ALICE, bad)
            ok = v.verdict == INDETERMINADO
        except Exception as e:
            ok, v = False, e
        check(f"calldata malformado ({bad[:16]!r}) → INDETERMINADO sem crash", ok, str(v)[:80])

    v = inv9_evaluate(ALICE)
    check("sem request e sem calldata → INDETERMINADO", v.verdict == INDETERMINADO)

    # tamper: esvaziar decodificadores não pode fabricar PASS
    import inv9_receiver_match as m
    saved = dict(m.VERIFIED_DECODERS)
    try:
        m.VERIFIED_DECODERS.clear()
        v = inv9_calldata(ALICE, make_depositv3(ALICE))
        check("tabela vazia → mesmo cenário benigno fica INDETERMINADO (fail-closed)", v.verdict == INDETERMINADO)
    finally:
        m.VERIFIED_DECODERS.update(saved)

    # ---------- orquestrador ----------
    print("\n[5] Orquestrador")
    v = inv9_evaluate(ALICE, request_receiver=BOB, calldata=make_depositv3(ALICE),
                      response_display=ALICE)
    check("request disponível TEM prioridade sobre calldata", v.layer == "request" and v.verdict == ALERT)
    check("orquestrador propaga deceptive_display", v.deceptive_display is True)

    v = inv9_evaluate(ALICE, calldata=make_depositv3(BOB))
    check("sem request: calldata decide (ALERT)", v.layer == "calldata" and v.verdict == ALERT)

    print("\n" + "=" * 78)
    if _failures:
        print(f"RESULTADO: {len(_failures)} FALHA(S)")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print("RESULTADO: TODOS OS TESTES INV9 PASSARAM")


if __name__ == "__main__":
    main()
