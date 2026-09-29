#!/usr/bin/env python3
"""ZEUS GUARD v4 — fuzz harness do motor QCSN.

Proposito adversarial: submeter o motor a entradas aleatorias e hostis
(extremos, colisoes exatas de arquétipos, empates, vetores degenerados) e
verificar invariante por invariante:

  INV1  Nenhuma excecao/crash em nenhuma entrada testada.
  INV2  Probabilidade sempre finita e em [0,1] (sem NaN/Inf).
  INV3  Veredito sempre em {BLOQUEAR, ALERTAR, LIBERAR}.
  INV4  Equivalencia quench vs argmin: mesmo veredito em TODAS as entradas
        (renova o experimento de honestidade sob adversidade).
  INV5  Determinismo: mesma entrada => mesmo veredito e mesma probabilidade.
  INV6  Robustez numerica: inputs com magnitude ate 1e300 nao causam overflow.

Uso: python3 engine/fuzz_engine.py [n_random] [seed]
"""
import json, os, sys, time, math, traceback
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from qcsn_risk_engine import QCSNRiskEngine as QCSNEngine, ARCHETYPES

N_RANDOM = int(sys.argv[1]) if len(sys.argv) > 1 else 50_000
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20260928
VERDICTS = {"BLOQUEAR", "ALERTAR", "LIBERAR"}

rng = np.random.default_rng(SEED)
eng = QCSNEngine()
D = len(next(iter(ARCHETYPES.values())))

failures = []
checked = 0


def check(x, tag):
    """Roda INV1..INV6 para um vetor de features; registra falhas nomeadas."""
    global checked
    checked += 1
    x = np.asarray(x, dtype=np.float64)
    try:  # INV1
        name, verdict, p, E = eng.classify(x)
        qname, qverdict, qp, qE = eng.classify_quench(x)
    except Exception as e:
        failures.append({"tag": tag, "inv": "INV1", "err": repr(e),
                         "x": x.tolist(), "trace": traceback.format_exc()[-400:]})
        return
    if not (math.isfinite(p) and 0.0 <= p <= 1.0):  # INV2
        failures.append({"tag": tag, "inv": "INV2", "p": p, "x": x.tolist()})
    if verdict not in VERDICTS or qverdict not in VERDICTS:  # INV3
        failures.append({"tag": tag, "inv": "INV3", "verdict": verdict,
                         "qverdict": qverdict, "x": x.tolist()})
    if verdict != qverdict:  # INV4
        failures.append({"tag": tag, "inv": "INV4", "verdict": verdict,
                         "qverdict": qverdict, "p": p, "qp": qp, "x": x.tolist()})
    # INV5 — re-execucao deterministica
    name2, verdict2, p2, _ = eng.classify(x)
    if verdict2 != verdict or p2 != p:
        failures.append({"tag": tag, "inv": "INV5", "p": p, "p2": p2, "x": x.tolist()})
    # INV6 — energias finitas mesmo sob inputs extremos
    if not np.all(np.isfinite(E)) or not np.all(np.isfinite(qE)):
        failures.append({"tag": tag, "inv": "INV6", "x": x.tolist()})


t0 = time.time()

# ---- frentes adversariais sistematicas ----
# F1: vertices dos arquétipos exatos (colisao intencional)
for k, v in ARCHETYPES.items():
    check(v, f"exact_{k}")

# F2: empates perfeitos entre pares de arquétipos (ponto medio)
names = list(ARCHETYPES)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        mid = (ARCHETYPES[names[i]] + ARCHETYPES[names[j]]) / 2.0
        check(mid, f"tie_{names[i]}_{names[j]}")

# F3: vetor equidistante de todos (empate global)
check(np.full(D, 0.5), "global_tie_0.5")

# F4: degenerados — zero, um, constantes
check(np.zeros(D), "zeros")
check(np.ones(D), "ones")
for c in (-1.0, 0.0, 0.25, 0.75, 1.5, 2.0):
    check(np.full(D, c), f"const_{c}")

# F5: extremos de magnitude (overflow de float64)
for mag in (1e10, 1e100, 1e300):
    check(rng.uniform(-mag, mag, D), f"magnitude_{mag:g}")
    check(np.full(D, mag), f"full_magnitude_{mag:g}")

# F6: tipos hostis — NaN/Inf individuais (deve ser detectado como invalido)
for pos in (0, D // 2, D - 1):
    v = np.full(D, 0.3)
    v[pos] = np.nan
    try:
        eng.classify(v)
        failures.append({"tag": f"nan_pos_{pos}", "inv": "INV7",
                         "err": "NaN aceito silenciosamente; classificador deve recusar"})
    except (ValueError, FloatingPointError):
        pass  # recusa explicita = comportamento correto

# F7: ruido gaussiano crescente sobre arquétipos (degeneracao gradual)
for sigma in (1e-9, 1e-3, 0.1, 0.5, 2.0, 10.0):
    for k in list(ARCHETYPES)[:3]:
        check(ARCHETYPES[k] + rng.normal(0, sigma, D), f"noise_{sigma:g}_{k}")

# ---- F8: monte carlo aleatorio uniforme ----
for _ in range(N_RANDOM):
    check(rng.uniform(0.0, 1.0, D), "random_uniform")
for _ in range(N_RANDOM):
    check(rng.uniform(-5.0, 5.0, D), "random_wide")

elapsed = time.time() - t0

receipt = {
    "timestamp": time.time(),
    "n_random_per_dist": N_RANDOM,
    "seed": SEED,
    "total_inputs_checked": checked,
    "invariants": ["INV1_no_crash", "INV2_prob_finite_unit", "INV3_verdict_valid",
                   "INV4_quench_argmin_equivalence", "INV5_determinism",
                   "INV6_finite_energy_extremes", "INV7_nan_rejected"],
    "failures": failures,
    "passed": len(failures) == 0,
    "elapsed_seconds": round(elapsed, 2),
}

out = os.path.join(os.path.dirname(__file__), "..", "evidence", "fuzz_engine_receipt.json")
with open(out, "w") as f:
    json.dump(receipt, f, indent=2)

print("=" * 66)
print("FUZZ HARNESS QCSN v4 — entradas adversariais + monte carlo")
print("=" * 66)
print(f"inputs verificados:     {checked}  (seed {SEED})")
print(f"invariantes checadas:  INV1..INV7")
print(f"falhas:                {len(failures)}")
for fl in failures[:10]:
    print(f"  -> {fl['tag']} | {fl['inv']}")
print(f"tempo:                 {elapsed:.2f}s")
print("-" * 66)
print(f"FUZZ RESULT: {'PASS — 0 falhas' if not failures else 'FAIL'}")
print("=" * 66)
sys.exit(0 if not failures else 1)
