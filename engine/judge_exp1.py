import numpy as np, time
from qcsn_risk_engine import QCSNRiskEngine, ARCHETYPES, RISK_OF, naive_baseline
rng = np.random.default_rng(42)

eng = QCSNRiskEngine()
names = eng.names; profiles = eng.profiles

def argmin_classify(x):
    E = ((profiles - x)**2).sum(axis=1)
    i = int(np.argmin(E))
    return names[i], RISK_OF[names[i]]

# reproduz exatamente o dataset do demo.py
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

kinds = ["DRAINER_APPROVAL","ADDRESS_POISONING","RISKY_BUT_LEGIT","LEGIT_SW","LEGIT_PAYMENT"]
dataset = [(k, make_tx(k)) for k in (kinds*8)]

diff = 0
for k, x in dataset:
    q = eng.classify(x)
    a = argmin_classify(x)
    if q[0] != a[0]:
        diff += 1
        print("DIVERGE:", k, "quench:", q[0], q[1], "argmin:", a[0], a[1])
print(f"\nEXPERIMENTO 1 (dataset do demo, 40 txs): quench diverge de argmin em {diff}/40 casos")

# timing quench vs argmin
t0=time.perf_counter(); [eng.classify(x) for k,x in dataset[:10]]; tq=(time.perf_counter()-t0)/10*1000
t0=time.perf_counter(); [argmin_classify(x) for k,x in dataset[:10]]; ta=(time.perf_counter()-t0)/10*1000
print(f"latencia quench: {tq:.2f} ms/tx | argmin: {ta:.4f} ms/tx | fator: {tq/ta:.0f}x mais lento")
