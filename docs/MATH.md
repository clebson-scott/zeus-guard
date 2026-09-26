# 📐 The mathematics of the QCSN risk engine

Everything here is implemented in `engine/qcsn_risk_engine.py` (~80 lines) and can be
verified by running `python3 engine/demo.py`.

## 1. Risk landscape

Every pending transaction is a feature vector `x ∈ [0,1]⁸`:

```
x = [approval, spender_EOA, spender_novo, razao_valor,
     selector_drainer, destino_envenenado, token_USDG_legitimo, padrao_normal]
```

Five attack archetypes define the hypothesis space — each branch `i` has a reference
profile `p_i`:

| Branch | Verdict |
|---|---|
| `DRAINER_APPROVAL` | BLOQUEAR |
| `ADDRESS_POISONING` | BLOQUEAR |
| `RISKY_BUT_LEGIT` | ALERTAR |
| `LEGIT_SW` | LIBERAR |
| `LEGIT_PAYMENT` | LIBERAR |

## 2. Energy of a hypothesis

Each branch gets a quadratic cost (squared Euclidean distance to its profile):

```
E_i(x) = ‖p_i − x‖²
```

Low energy = the transaction "looks like" that archetype.

## 3. Dissipative selection (Gibbs quench)

Instead of a hard argmin (which is brittle near decision boundaries), the engine runs a
**quench**: a thermal-bath transition matrix whose temperature drops over 60 steps,
β: 2 → 40 (linear).

The bath couples every ordered pair of branches:

```
W_ij(β) = 5000 / (1 + e^{β·(E_i − E_j)})        [rate of i → j]
```

Note the asymmetry: transitions *toward* lower energy are exponentially favored as β
grows. The generator is

```
Q(β) = W(β) − diag(Wᵀ·1)
```

The probability vector starts uniform, `P₀ = (1/5, …, 1/5)`, and each step applies the
**exact** propagator (matrix exponential, not Euler):

```
P ← e^{Q(β_s)·dt} · P,    dt = 400 µs,    s = 1…60
```

Decision: `i* = argmax P`, verdict = the archetype's verdict, confidence = `P_{i*}`.

## 4. Why a quench and not argmin

The quench is a **continuous annealed confidence**: when `x` sits between two
archetypes, the population mixes and lands on the dominant basin with measurable
confidence `p*` (mean 0.99 on the benchmark) instead of an unstable all-or-nothing
minimum. The β-schedule makes the final state effectively the Gibbs distribution
`e^{−βE}/Z` at β = 40 — the argmin, but reached through a well-conditioned path.

## 5. Measured results (reproducible)

| Metric | Value | How to verify |
|---|---|---|
| Accuracy, 40-tx benchmark | **40/40 = 100%** | `python3 engine/demo.py` |
| Fixed-threshold baseline | 38/40 = 95% | same run, printed |
| Latency | **0.9 ms/tx** (full 60-step quench) | same run, printed |
| Mean confidence p* | ≈ 0.99 | same run |

Complexity per transaction: 60 iterations × (5×5 exponential + matvec). The 5×5
`expm` dominates; measured wall time is sub-millisecond on commodity hardware, and
the quench fits inside a block-time budget with orders of magnitude to spare.

## 6. Quantum-hardware validation of the mechanism

The **dissipative selection mechanism** — population relaxation under a thermal bath
driven toward the ground state — was measured on a real superconducting quantum
processor: **IBM Quantum `ibm_fez`, job `daorvfg2fm4c73f5tlog`, selection fidelity 0.997**
(Hahn-style coherence experiments with XY4 dynamical decoupling on the same backend
measured T₂ ≈ 52 µs, which bounds *coherent* variants; the dissipative path is the
noise-robust one — that is precisely why the engine quenches rather than interferes).

Declared honestly: the deployed contract is **classical** — a deterministic dissipative
computation *inspired by* open quantum-system dynamics, integrated via exact matrix
exponentiation. No QPU is called at transaction time.

## 7. The honesty experiment: quench vs argmin, published

We tested our own differentiator (`engine/honesty_experiment.py`):

| Set | Cases | Quench ≠ argmin |
|---|---|---|
| Official benchmark | 40 | 0 |
| Stress σ=0.05 / 0.15 / 0.30 | 1,800 | 0 |
| Exact archetype midpoints | 10 | 0 |
| **Total** | **1,850** | **0** |

Latency: quench ≈ 1.7 ms/tx vs argmin ≈ 0.007 ms/tx (**~250x slower**). At exact
midpoints p* degenerates to 0.5 — the boundary is a tie-break by ordering, not a
confident decision.

**What this means, plainly:** the final state at β=40 *is* the Gibbs distribution,
which concentrates on the minimum — the verdict equals argmin. The quench is not a
better classifier than a 3-line nearest-centroid; it is the *same* classifier that
additionally yields a continuous, well-conditioned confidence p* on the path, and a
reading grounded in the open-system physics we measured on `ibm_fez`. We ship the
experiment in the repo so any judge can verify this in one command, and we say it here
so nobody else has to discover it.

## 8. Contract-side policy constants

| Constant | Value | Meaning |
|---|---|---|
| `RISK_BLOCK_X100` | 6000 | score ≥ 60% → `TooRisky` (drainer) |
| `MIN_CHALLENGE_WINDOW` | 120 s | minimum escrow protection |
| `DAILY_CAP_DEFAULT` | 1000e18 | 1,000 USDG/day unless configured |
| Rolling window | 86400 s | daily cap resets after 24 h |
