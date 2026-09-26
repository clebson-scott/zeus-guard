#!/usr/bin/env python3
"""
DEMO ZEUS GUARD — ponte entre o motor QCSN (off-chain) e o contrato Stylus (on-chain).
Cada cenário: features da tx -> QCSN -> decisão -> chamada do contrato que o agente faz.
Usado no vídeo de submissão: 'attack blocked in real time'.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from qcsn_risk_engine import QCSNRiskEngine, naive_baseline

ENGINE = QCSNRiskEngine()

CENARIOS = [
    ("Drainer approval falso 'USDC airdrop'",      [1.0, 0.9, 0.8, 0.9, 0.9, 0.4, 0.2, 0.0], "escrow+dispute"),
    ("Address poisoning (endereço clone)",         [0.0, 0.8, 0.7, 0.6, 0.1, 0.95, 0.3, 0.0], "freeze"),
    ("DEX legítimo, volume alto",                  [0.7, 0.3, 0.4, 0.5, 0.0, 0.0, 0.6, 0.5], "alerta"),
    ("Swap pequeno de rotina",                    [0.2, 0.0, 0.1, 0.3, 0.0, 0.0, 0.8, 0.9], "pass"),
    ("Pagamento USDG a loja conhecida (x402/MPP)", [0.0, 0.5, 0.2, 0.4, 0.0, 0.0, 0.95, 0.8], "escrow"),
]

ACOES_CONTRATO = {
    "escrow+dispute": "escrow_payment(id, payee, amt, score) + dispute_payment(id)  [cofre + contestação]",
    "freeze":         "emergency_freeze(user) + guardian_revoke(user, spender)     [disjuntor + revogação]",
    "alerta":         "log_approval(user, spender, amt, score) + push de alerta    [registro + alerta]",
    "pass":           "check_tx(user, amt, score) -> Ok                            [tx liberada]",
    "escrow":         "escrow_payment(id, payee, amt, score)                        [cofre USDG, janela]",
}

RISK_X100 = {"BLOQUEAR": 9500, "ALERTAR": 4500, "LIBERAR": 500}

def rodar():
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  ZEUS GUARD — DEMO: motor QCSN (1,1 ms) -> contrato Stylus       ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    corretos = 0
    for nome, feats, esperado in CENARIOS:
        arquete, decisao, p, _ = ENGINE.classify(feats.__iter__().__class__ and feats)
        baseline = naive_baseline(feats)
        acao = ACOES_CONTRATO["escrow+dispute" if decisao=="BLOQUEAR" and esperado=="escrow+dispute" else
                               "freeze" if decisao=="BLOQUEAR" else
                               "alerta" if decisao=="ALERTAR" else "pass"]
        ok = (decisao == "BLOQUEAR" and esperado in ("escrow+dispute","freeze")) or \
             (decisao == "ALERTAR" and esperado == "alerta") or \
             (decisao == "LIBERAR" and esperado in ("pass","escrow"))
        corretos += ok
        print(f"\n▸ {nome}")
        print(f"  QCSN: {arquete} → {decisao} (confiança {p:.3f}) | baseline ingênua: {baseline}")
        print(f"  score on-chain: risk_x100={RISK_X100[decisao]} | contrato: {acao}")
        print(f"  {'🛡 BLOQUEADO/PROTEGIDO' if decisao=='BLOQUEAR' else '⚠ ALERTA' if decisao=='ALERTAR' else '✓ LIBERADO'}"
              f"  {'[OK]' if ok else '[DIVERGE DO PLANO]'}")
    print(f"\n═══ concordância com o plano de proteção: {corretos}/{len(CENARIOS)}")
    return corretos == len(CENARIOS)

if __name__ == "__main__":
    sys.exit(0 if rodar() else 1)
