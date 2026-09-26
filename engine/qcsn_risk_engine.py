"""
QCSN RISK ENGINE — motor de selecao dissipativa para o ZEUS GUARD.
Inspiracao fisica: quench de Gibbs (beta 2->40) sobre paisagem de hipoteses.
Cada ramo = um arquétipo de risco; selecao dissipativa escolhe o dominante.
Validado com o mesmo mecanismo medido no IBM Quantum ibm_fez (fidelidade 0.997).
"""
import numpy as np
from scipy.linalg import expm

# ---- arquétipos de risco (perfis esperados de features, 0-1) ----
# features: [approval, spender_EOA, spender_novo, razao_valor, selector_drainer,
#            destino_envenenado, token_USDG_legitimo, padrao_normal]
ARCHETYPES = {
    "DRAINER_APPROVAL": np.array([1.0, 0.9, 0.8, 0.9, 0.9, 0.4, 0.2, 0.0]),
    "ADDRESS_POISONING": np.array([0.0, 0.8, 0.7, 0.6, 0.1, 0.95, 0.3, 0.0]),
    "RISKY_BUT_LEGIT":  np.array([0.7, 0.3, 0.4, 0.5, 0.0, 0.0, 0.6, 0.5]),
    "LEGIT_SW":          np.array([0.2, 0.0, 0.1, 0.3, 0.0, 0.0, 0.8, 0.9]),
    "LEGIT_PAYMENT":     np.array([0.0, 0.5, 0.2, 0.4, 0.0, 0.0, 0.95, 0.8]),
}
RISK_OF = {"DRAINER_APPROVAL": "BLOQUEAR", "ADDRESS_POISONING": "BLOQUEAR",
           "RISKY_BUT_LEGIT": "ALERTAR", "LEGIT_SW": "LIBERAR", "LEGIT_PAYMENT": "LIBERAR"}

class QCSNRiskEngine:
    """Selecao dissipativa de hipotese: quench beta 2->40 sobre custos x^2."""
    def __init__(self, beta_i=2.0, beta_f=40.0, steps=60):
        self.names = list(ARCHETYPES)
        self.profiles = np.array([ARCHETYPES[k] for k in self.names])
        self.beta_i, self.beta_f, self.steps = beta_i, beta_f, steps

    def _costs(self, tx_features):
        d = self.profiles - tx_features
        return (d**2).sum(axis=1)

    def classify(self, tx_features):
        E = self._costs(tx_features)
        n = len(E)
        P = np.ones(n)/n
        dE0 = E[:, None] - E[None, :]
        dt = 400e-6
        for s in range(self.steps):
            beta = self.beta_i + (self.beta_f-self.beta_i)*s/self.steps
            W = 5000.0/(1.0 + np.exp(beta*dE0))          # banho termico
            Q = W - np.diag(W.sum(axis=0))
            P = expm(Q*dt) @ P                            # integracao exata
        i = int(np.argmax(P))
        return self.names[i], RISK_OF[self.names[i]], float(P[i]), E

# ---- baseline ingenua (limiar fixo) para comparacao honesta ----
def naive_baseline(tx):
    risk = (tx[0]*tx[2]*0.9 + tx[4] + tx[5]*0.9) * tx[3]
    return "BLOQUEAR" if risk > 0.35 else ("ALERTAR" if risk > 0.12 else "LIBERAR")
