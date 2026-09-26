"""DEMO ZEUS GUARD — dataset sintetico de ataques reais + benchmark motor vs baseline."""
import numpy as np, time
from qcsn_risk_engine import QCSNRiskEngine, naive_baseline

rng = np.random.default_rng(42)

def make_tx(kind):
    if kind == "DRAINER_APPROVAL":
        return np.clip([1, .9, rng.uniform(.7,.95), rng.uniform(.8,1), rng.uniform(.8,1),
                        rng.uniform(.2,.6), rng.uniform(0,.4), rng.uniform(0,.15)] + rng.normal(0,.05,8), 0, 1)
    if kind == "ADDRESS_POISONING":
        return np.clip([0, rng.uniform(.6,.95), rng.uniform(.5,.9), rng.uniform(.4,.8), rng.uniform(0,.2),
                        rng.uniform(.85,1), rng.uniform(.1,.5), rng.uniform(0,.1)] + rng.normal(0,.05,8), 0, 1)
    if kind == "RISKY_BUT_LEGIT":
        return np.clip([rng.uniform(.5,.8), rng.uniform(.1,.5), rng.uniform(.2,.6), rng.uniform(.3,.7), 0,
                        0, rng.uniform(.4,.8), rng.uniform(.3,.7)] + rng.normal(0,.05,8), 0, 1)
    if kind == "LEGIT_SW":
        return np.clip([rng.uniform(0,.4), 0, rng.uniform(0,.2), rng.uniform(.1,.5), 0, 0,
                        rng.uniform(.6,1), rng.uniform(.7,1)] + rng.normal(0,.05,8), 0, 1)
    return np.clip([0, rng.uniform(.3,.7), rng.uniform(0,.3), rng.uniform(.2,.6), 0, 0,
                    rng.uniform(.8,1), rng.uniform(.6,1)] + rng.normal(0,.05,8), 0, 1)

kinds = ["DRAINER_APPROVAL", "ADDRESS_POISONING", "RISKY_BUT_LEGIT", "LEGIT_SW", "LEGIT_PAYMENT"]
truth_of = {"DRAINER_APPROVAL": "BLOQUEAR", "ADDRESS_POISONING": "BLOQUEAR",
            "RISKY_BUT_LEGIT": "ALERTAR", "LEGIT_SW": "LIBERAR", "LEGIT_PAYMENT": "LIBERAR"}

engine = QCSNRiskEngine()
dataset = [(k, make_tx(k)) for k in (kinds*8)]          # 40 txs
rng.shuffle(dataset)

hits_q, hits_n, t_list = 0, 0, []
print(f"{'TX':>3} {'ARQUETIPO REAL':<18} {'QCSN':<18} {'BASELINE':<10} {'p*':<6} {'ms':>6}")
for i, (kind, tx) in enumerate(dataset):
    t0 = time.perf_counter()
    name, verdict, p, _ = engine.classify(tx)
    dt_ms = (time.perf_counter()-t0)*1000
    t_list.append(dt_ms)
    nv = naive_baseline(tx)
    ok_q = verdict == truth_of[kind]; ok_n = nv == truth_of[kind]
    hits_q += ok_q; hits_n += ok_n
    mark = "OK " if ok_q else "XX "
    print(f"{i:>3} {kind:<18} {verdict:<18} {nv:<10} {p:<6.3f} {dt_ms:>6.1f} {mark}")

print(f"\nACURACIA QCSN:   {hits_q}/{len(dataset)} = {100*hits_q/len(dataset):.1f}%")
print(f"ACURACIA LIMIAR: {hits_n}/{len(dataset)} = {100*hits_n/len(dataset):.1f}%")
print(f"LATENCIA MEDIA:  {np.mean(t_list):.1f} ms/tx (quench completo de 60 passos)")
