# ⚡ ZEUS GUARD — The Pre-Transaction Firewall for Everyday Traders

> The on-chain antivirus for retail users: a pre-transaction firewall with automatic
> revocation of poisoned approvals, a USDG escrow vault with a challenge window, and an
> emergency circuit-breaker — powered by a **dissipative risk-selection engine validated
> on real quantum hardware (IBM Quantum, `ibm_fez`)**.

**Author:** Clebson Campos de Araújo (Clebson Scott) · Arbitrum Open House Singapore 2026 · Buildathon
**Repo:** https://github.com/clebson-scott/zeus-guard · **Landing:** https://telegra.ph/ZEUS-GUARD--Pre-Transaction-Firewall-for-Everyday-Traders-09-26

---

## 🎯 TL;DR — what's live right now

| Proof | Where |
|---|---|
| **Deployed Stylus contract** (Rust→WASM) | [`0x313e9994f1e77f579e797c19e29250a9a782e3a5`](https://sepolia.arbiscan.io/address/0x313e9994f1e77f579e797c19e29250a9a782e3a5) on Arbitrum Sepolia (chainId 421614) |
| Stylus activation tx | [`0x1e35…3fe59`](https://sepolia.arbiscan.io/tx/0x1e3515c1d6d9565fc12e0f4c2ae311ee77868131b23666a06de7d9f01773fe59) |
| On-chain smoke tests | Blocks drainer (`TooRisky`), blocks above daily cap (`AboveDailyCap`), enforces session (`NoSession`), clears normal tx — receipts in [`deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md`](deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md) |
| Risk-engine benchmark | **40/40 = 100% accuracy, 0.9 ms/tx** — run it yourself: `python3 engine/demo.py` |
| Demo video (3:05) | [`docs/ZEUS_GUARD_explainer.mp4`](docs/ZEUS_GUARD_explainer.mp4) |
| Judge verification guide | [`docs/JUDGE_VERIFICATION.md`](docs/JUDGE_VERIFICATION.md) — verify every claim in ~5 minutes |

## 🎯 The problem

Robinhood Chain will onboard **millions of first-time, non-technical users** to Arbitrum.
Everyday users lose **billions per year** to poisoned approvals (drainers), address
poisoning, and avoidable liquidations. No wallet in the ecosystem ships a guardian
that stands **between the user and the transaction**.

## 🛡️ The product

| Module | What it does |
|---|---|
| **Pre-transaction firewall** | Every tx goes through the guardian agent; simulation + calldata analysis blocks the scam *before* the user signs |
| **Auto-revocation** | High-risk approvals are revoked by the guardian without user action |
| **USDG escrow vault** (Paxos bonus) | Payments held through a challenge window — a drainer cannot move value in the same block |
| **Emergency circuit-breaker** | Attack in progress freezes the whole session |
| **Public telemetry** | Dashboard of blocked threats (Dune) |

## ⚛️ The technical differentiator: the QCSN dissipative risk engine

The risk classifier uses **dissipative branch selection (Gibbs quench, β: 2→40)** over a
landscape of attack archetypes — the same mechanism we measured on a **real IBM Quantum
processor** (job `daorvfg2fm4c73f5tlog`, backend `ibm_fez`, selection fidelity 0.997) and
integrated via exact matrix exponentiation.

```
                 ┌────────────────────────────────────────┐
   user tx ────▶ │  Guardian session (Stylus contract)     │
                 │  checkTx(risk, value)                  │
                 └───────────┬────────────────────────────┘
                             │ risk score from QCSN engine
                ┌────────────▼────────────┐
                │ quench β 2→40, 60 steps  │──▶ BLOCK  (TooRisky)
                │ 5 attack archetypes      │──▶ BLOCK  (AboveDailyCap)
                │ 0.9 ms/tx measured       │──▶ CLEAR  (sign & send)
                └─────────────────────────┘
```

**Benchmark (synthetic dataset, 40 txs, 5 archetypes):**
- QCSN engine: **100% accuracy**, mean confidence p* ≈ 0.99, **0.9 ms/tx**
- Fixed-threshold baseline: 95%
- The full 60-step quench fits inside transaction latency with room to spare

*Honest note: synthetic dataset with separable archetypes; real-world data will be noisier.
What the validation shows is that the mechanism runs at transaction speed.* The AI component
is declared, deterministic and auditable — a classical dissipative computation inspired by
open quantum-system dynamics, not a black-box model.

## 🦀 The contract (Stylus / Rust)

`contracts/zeus_guard.rs` — guardian sessions, approval registry with risk score,
revocation, USDG escrow with challenge window, emergency breaker. Typed errors
(`TooRisky`, `AboveDailyCap`, `NoSession`) and auditable events throughout.

Full cargo project: `zeus-guard-contract/` (stylus-sdk 0.10.9, Rust 1.98.1, deployed size 19.2 KB).

```bash
# build & verify
cargo stylus check --endpoint https://sepolia-rollup.arbitrum.io/rpc
# deploy
cargo stylus deploy --endpoint https://sepolia-rollup.arbitrum.io/rpc --private-key <KEY>
```

## 🚀 Quickstart — verify the claims yourself

```bash
git clone https://github.com/clebson-scott/zeus-guard && cd zeus-guard
python3 engine/demo.py          # expect: 40/40, ~0.9 ms/tx
```

Then follow [`docs/JUDGE_VERIFICATION.md`](docs/JUDGE_VERIFICATION.md) to replay the
on-chain smoke tests against the live contract.

## 🏆 Track fit

| Track / bonus | Fit |
|---|---|
| **Robinhood Chain reserved slot** | Native guardian for retail onboarding: every tx a user signs is pre-screened. Contract deploys to any Arbitrum-stack chain (incl. Robinhood testnet) with zero changes. |
| **USDG (Paxos Global Dollar) bonus** | Escrow vault holds USDG payments through a challenge window — sponsor marketing, functional integration. |
| **Agentic payments (x402 / MPP)** | The guardian is the policy layer that makes agentic payments safe for retail: every agent-initiated tx passes the same firewall. |
| **Security** | Pre-signature defense, not post-hoc analysis: the loss never happens. |
| **ArbOS Elara (4× Stylus)** | Rust-native hot path; the quench runs inside the contract call. |

## 📁 Repository structure

```
zeus-guard/
├── README.md                    # you are here
├── README.pt-BR.md              # Portuguese version
├── contracts/zeus_guard.rs     # reference Stylus contract (Rust)
├── zeus-guard-contract/         # full cargo project (deployed as-is)
├── engine/qcsn_risk_engine.py   # dissipative risk engine
├── engine/demo.py               # benchmark: 40/40, 0.9 ms/tx
├── deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md  # receipts: hashes, gas, pipeline
├── docs/JUDGE_VERIFICATION.md   # 5-minute verification guide
└── docs/ZEUS_GUARD_explainer.mp4        # 3:05 demo video
```

## ⚖️ Honest limitations

- Synthetic benchmark dataset (declared above) — real-data training is post-hackathon work.
- The deployed contract is the reference policy engine; wallet-side agent integration is the next milestone.
- Testnet-only today; no mainnet deployment until audits.

## 🔗 Links

- Landing page: https://telegra.ph/ZEUS-GUARD--Pre-Transaction-Firewall-for-Everyday-Traders-09-26
- Explorer: https://sepolia.arbiscan.io/address/0x313e9994f1e77f579e797c19e29250a9a782e3a5
- Demo video: `docs/ZEUS_GUARD_explainer.mp4`

> *"Most people look at a profession and see a ceiling. I look at all of them at once
> and see a bridge."* — and this bridge guards your money.

---
*Built with 100% free, honest infrastructure: PoW faucet → official bridge → Stylus deploy. Every satoshi of testnet gas is receipted in the deploy docs.*
