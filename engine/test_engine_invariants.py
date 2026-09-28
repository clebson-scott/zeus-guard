#!/usr/bin/env python3
"""SUITE DE TESTES DE INVARIANTES DO MOTOR QCSN E BENCHMARK.

Garante que as propriedades matematicas, causais e numericas do ZEUS GUARD
permanecem validas sob condicoes adversariais.
"""
import unittest
import numpy as np
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from qcsn_risk_engine import QCSNRiskEngine, ARCHETYPES, RISK_OF
from realdata_benchmark import features, KNOWN_PROTOCOLS, DRAINER_SELECTORS


class TestQCSNEngineInvariants(unittest.TestCase):

    def setUp(self):
        self.engine = QCSNRiskEngine()
        self.rng = np.random.default_rng(2026)

    def test_invariance_quench_vs_analytical(self):
        """Invariante 1: O caminho analitico (classify) e o quench numerico (classify_quench)
        produzem o mesmo verdicto de risco para amostras estresse com ruido."""
        kinds = list(RISK_OF)
        for _ in range(200):
            kind = self.rng.choice(kinds)
            base = ARCHETYPES[kind]
            x = np.clip(base + self.rng.normal(0, 0.15, 8), 0, 1)

            c_arch, c_verdict, c_p, _ = self.engine.classify(x)
            q_arch, q_verdict, q_p, _ = self.engine.classify_quench(x)

            # O verdicto de risco (BLOQUEAR, ALERTAR, LIBERAR) deve ser rigorosamente identico
            self.assertEqual(c_verdict, q_verdict, f"Verdicto diverge para vector {x}: c={c_verdict}, q={q_verdict}")

    def test_probability_normalization_and_finiteness(self):
        """Invariante 2: As probabilidades p* devem ser sempre finitas, positivas e no intervalo (0, 1]."""
        for _ in range(100):
            x = self.rng.uniform(-1, 2, 8)  # inclui valores fora de [0, 1]
            c_arch, c_verdict, c_p, E_c = self.engine.classify(x)
            q_arch, q_verdict, q_p, E_q = self.engine.classify_quench(x)

            self.assertTrue(np.isfinite(c_p), "Probabilidade c_p nao e finita")
            self.assertTrue(np.isfinite(q_p), "Probabilidade q_p nao e finita")
            self.assertGreater(c_p, 0.0)
            self.assertLessEqual(c_p, 1.0)
            self.assertGreater(q_p, 0.0)
            self.assertLessEqual(q_p, 1.0)

    def test_extreme_input_no_runtime_warnings(self):
        """Invariante 3: Vetores de features com valores extremamente grandes nao causam overflow ou nan."""
        x_extreme = np.array([1000.0, -1000.0, 500.0, -500.0, 1000.0, -1000.0, 500.0, -500.0])

        # Testar caminho analitico e quench
        arch_c, verdict_c, p_c, _ = self.engine.classify(x_extreme)
        arch_q, verdict_q, p_q, _ = self.engine.classify_quench(x_extreme)

        self.assertIn(arch_c, self.engine.names)
        self.assertIn(arch_q, self.engine.names)
        self.assertTrue(np.isfinite(p_c))
        self.assertTrue(np.isfinite(p_q))

    def test_monotonic_risk_response(self):
        """Invariante 4: Incrementar flags de ataque (selector_drainer=1, spender_eoa=1, ratio=1)
        deve estritamente aproximar o vetor do arquetipo DRAINER_APPROVAL."""
        x_legit = np.array([0.0, 0.0, 0.0, 0.1, 0.0, 0.0, 0.9, 0.9])
        x_attack = np.array([1.0, 1.0, 0.8, 1.0, 1.0, 0.0, 0.2, 0.0])

        E_legit = self.engine._costs(x_legit)
        E_attack = self.engine._costs(x_attack)

        drainer_idx = self.engine.names.index("DRAINER_APPROVAL")
        self.assertLess(E_attack[drainer_idx], E_legit[drainer_idx],
                        "Vetor de ataque deveria ter custo menor para DRAINER_APPROVAL")

    def test_dataset_ground_truth_integrity(self):
        """Invariante 5: O dataset de benchmark contem labels de ground truth coerentes
        sem falsos positivos em DEX Routers conhecidos."""
        DATA = os.path.join(os.path.dirname(__file__), "data")
        with open(os.path.join(DATA, "real_labeled_approves.json"), "r") as f:
            labeled = json.load(f)

        for r in labeled:
            sp = r.get("spender", "").lower()
            if sp in KNOWN_PROTOCOLS:
                self.assertEqual(r.get("label"), "BENIGN",
                                 f"DEX Router {sp} nao pode ser rotulado como ATTACK no ground truth")


if __name__ == "__main__":
    unittest.main()
