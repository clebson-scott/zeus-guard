import numpy as np
from qcsn_risk_engine import QCSNRiskEngine, ARCHETYPES, RISK_OF, naive_baseline

eng = QCSNRiskEngine(); names = eng.names; profiles = eng.profiles
TRUTH = {"DRAINER_APPROVAL":"BLOQUEAR","ADDRESS_POISONING":"BLOQUEAR","RISKY_BUT_LEGIT":"ALERTAR","LEGIT_SW":"LIBERAR","LEGIT_PAYMENT":"LIBERAR"}

def argmin_classify(x):
    E = ((profiles-x)**2).sum(axis=1); i=int(np.argmin(E)); return names[i]

def make_tx(kind, sigma):
    base = {
    "DRAINER_APPROVAL":[1,.9,.85,.9,.9,.4,.2,0],
    "ADDRESS_POISONING":[0,.8,.7,.6,.1,.95,.3,0],
    "RISKY_BUT_LEGIT":[.7,.3,.4,.5,0,0,.6,.5],
    "LEGIT_SW":[.2,0,.1,.3,0,0,.8,.9],
    "LEGIT_PAYMENT":[0,.5,.2,.4,0,0,.95,.8]}[kind]
    return np.clip(np.array(base)+np.random.normal(0,sigma,8),0,1)

for sigma in (0.05, 0.15, 0.30):
    np.random.seed(7)
    N=600
    data=[(k,make_tx(k,sigma)) for k in np.random.choice(list(TRUTH),N)]
    q_ok=a_ok=b_ok=0; div=0
    for k,x in data:
        qv = RISK_OF[eng.classify(x)[0]]; av = RISK_OF[argmin_classify(x)]; bv = naive_baseline(x)
        q_ok+= qv==TRUTH[k]; a_ok+= av==TRUTH[k]; b_ok+= bv==TRUTH[k]
        if eng.classify(x)[0]!=argmin_classify(x): div+=1
    print(f"sigma={sigma:.2f}: QCSN {100*q_ok/N:.1f}% | argmin {100*a_ok/N:.1f}% | baseline {100*b_ok/N:.1f}% | divergencias quench-vs-argmin: {div}/{N}")

# ponto exatamente no meio de dois centroides
mid = (ARCHETYPES["DRAINER_APPROVAL"]+ARCHETYPES["ADDRESS_POISONING"])/2
print("\nmidpoint DRAINER/POISONING -> quench:", eng.classify(mid)[0], "p*=", round(eng.classify(mid)[2],3), "| argmin:", argmin_classify(mid))
mid2 = (ARCHETYPES["LEGIT_SW"]+ARCHETYPES["LEGIT_PAYMENT"])/2
print("midpoint LEGIT_SW/LEGIT_PAYMENT -> quench:", eng.classify(mid2)[0], "p*=", round(eng.classify(mid2)[2],3), "| argmin:", argmin_classify(mid2))
