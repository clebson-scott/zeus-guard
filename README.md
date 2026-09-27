# ⚡ ZEUS GUARD — The Pre-Transaction Firewall for Everyday Traders

> The on-chain antivirus for retail users: a pre-transaction firewall with revocation of
> poisoned approvals, a USDG escrow vault with a challenge window, and an emergency
> circuit-breaker — powered by a **fast, deterministic risk engine** (with a quench-style
> dissipative selector whose quantum-hardware validation we keep as open research).
> No mystery math: the production engine is a measured argmin, benchmarked in the open.

**Author:** Clebson Campos de Araújo (Clebson Scott) · Arbitrum Open House Singapore 2026 · Buildathon
**Repo:** https://github.com/clebson-scott/zeus-guard · **Landing:** https://telegra.ph/ZEUS-GUARD--Pre-Transaction-Firewall-for-Everyday-Traders-09-26

---

## 🎯 TL;DR — what's live right now

| Proof | Where |
|---|---|
| **Deployed Stylus contract v2** (Rust→WASM) | [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a) on Arbitrum Sepolia (chainId 421614) |
| Stylus activation tx | [`0x2e65…1978`](https://sepolia.arbiscan.io/tx/0x2e658e8abb37549d42671da8970bc3b06f053c2c83bc2d03ed72c00033f51978) |
| On-chain smoke tests | Blocks drainer (`TooRisky`), blocks above daily cap (`AboveDailyCap`), enforces session (`NoSession`), clears normal tx — v2 receipts in [`deploy/DEPLOYADO_V2_ARBITRUM_SEPOLIA.md`](deploy/DEPLOYADO_V2_ARBITRUM_SEPOLIA.md) · v1 receipts in [`deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md`](deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md) |
| Risk-engine benchmark | **40/40 = 100% accuracy, <0.1 ms/tx** (analytic path: argmin + exact Gibbs probability) — run it yourself: `python3 engine/demo.py` |
| Demo video (3:05) | [`docs/ZEUS_GUARD_explainer.mp4`](docs/ZEUS_GUARD_explainer.mp4) |
| **v1 contract (historical)** | [`0x313e9994f1e77f579e797c19e29250a9a782e3a5`](https://sepolia.arbiscan.io/address/0x313e9994f1e77f579e797c19e29250a9a782e3a5) — first deployment, receipts kept in [`deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md`](deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md) |
| **Live web demo** | open [`demo/index.html`](demo/index.html) in a browser — every button queries the real contract, no wallet needed |
| **Retail wallet mock** | open [`demo/wallet.html`](demo/wallet.html) — the consumer UX with the guardian plugged in: send flow, drainer / address-poisoning / over-cap attempts blocked live by the on-chain policy |
| **Real wallet integration (EIP-1193)** | same page: connect MetaMask or any EIP-1193 wallet (Robinhood Chain profile included) and the on-chain policy screens **your own address** — read-only, no signatures ever requested |
| **v3 contract source (fixes found by adversarial review)** | [`zeus-guard-contract/src/lib.rs`](zeus-guard-contract/src/lib.rs) — risk now enforced **in the escrow path**, real `vault_send` choke point, dispute deadline (`DisputeExpired`), typed `AmountTooLarge` instead of panic |
| Native Rust unit tests | `cd zeus-guard-contract && cargo test` — policy math tested natively, **11/11** (incl. v3 gates: overflow, saturating risk, money-path firewall, dispute deadline) |
| **Real chain screening** | `python3 engine/real_features.py --rpc https://arb1.arbitrum.io/rpc --user ... --to ... --data 0x...` — the 8 features are read from **live chain state** (getCode, nonce, real balance, poisoning look-alike heuristic) |
| **Live attack & defense proof** | `python3 proof/live_attack_defense.py --rpc https://sepolia-rollup.arbitrum.io/rpc --contract 0x0384...` — 4/4 PASS against the deployed contract (revert data decoded on-screen) |
| Honesty experiment | `python3 engine/honesty_experiment.py` — quench vs argmin: **0 divergences in 1,850 cases**, 252x slower; declared in the open, not hidden |
| Judge verification guide | [`docs/JUDGE_VERIFICATION.md`](docs/JUDGE_VERIFICATION.md) — verify every claim in ~5 minutes |
| Architecture & trust model | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — who runs what, why the guardian cannot be bypassed |
| Engine math | [`docs/MATH.md`](docs/MATH.md) — the dissipative quench, from equations to measured numbers |

## 🎯 The problem

Robinhood Chain will onboard **millions of first-time, non-technical users** to Arbitrum.
Everyday users lose **billions per year** to poisoned approvals (drainers), address
poisoning, and avoidable liquidations. No wallet in the ecosystem ships a guardian
that stands **between the user and the transaction**.

## 🛡️ The product

| Module | What it does |
|---|---|
| **Pre-transaction firewall** | Every tx goes through the guardian agent; simulation + calldata analysis blocks the scam *before* the user signs |
| **Revocation registry** | `guardian_revoke` marks the approval as revoked **publicly on-chain** (`approval_status_pub`, v4). Wallets, agents and the guardian read the registry before signing — that is real enforcement at the signing layer. For EOA approvals the chain itself cannot revoke an existing allowance (only the owner can) — we say so; the vault is the enforced choke point for value |
| **USDG escrow vault** (Paxos bonus) | Payments pulled via real `IERC20.transferFrom` and held through a challenge window — a drainer cannot move value in the same block; the guardian can dispute and refund |
| **Emergency circuit-breaker** | Attack in progress freezes the whole session |
| **Public telemetry** | Every verdict emits auditable on-chain events — a Dune dashboard rendering them is on the roadmap (events shipped today, dashboard next) |

## ⚛️ The QCSN risk engine: honest by construction

The risk classifier is **deterministic nearest-archetype selection over squared costs**
(argmin) with an exact Gibbs confidence at final temperature. The quench-style dissipative
selector (β: 2→40, 60 steps) is **provably equivalent** — 0 divergences across every case
tested ([`engine/honesty_experiment.py`](engine/honesty_experiment.py)) — so production
takes the fast path and keeps the quench for research reproduction. The mechanism was
first measured on a real IBM Quantum processor (job `daorvfg2fm4c73f5tlog`, backend
`ibm_fez`, selection fidelity 0.997); the quantum hardware is our research origin, **not**
a production dependency, and we state that openly.

```
                 ┌────────────────────────────────────────┐
   user tx ────▶ │  Guardian session (Stylus contract)     │
                 │  checkTx(risk, value)                  │
                 └───────────┬────────────────────────────┘
                             │ risk score from QCSN engine
                ┌────────────▼────────────┐
                │ argmin + exact Gibbs     │──▶ BLOCK  (TooRisky)
                │ 5 attack archetypes      │──▶ BLOCK  (AboveDailyCap)
                │ <0.1 ms/tx measured      │──▶ CLEAR  (sign & send)
                └─────────────────────────┘
```

**Benchmark (synthetic dataset, 40 txs, 5 archetypes):**
- QCSN engine: **100% accuracy**, mean confidence p* ≈ 1.00, **<0.1 ms/tx** (analytic path; the 60-step quench measured 0.9-1.7 ms and produces the identical verdict)
- Fixed-threshold baseline: 95%

**Who computes the risk?** The agent judges, the contract enforces — full trust model in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#who-computes-the-risk-the-trust-model-stated-plainly).

Honest note: synthetic dataset with separable archetypes; real-world data will be noisier.
What the validation shows is that the mechanism runs at transaction speed.* The AI component
is declared, deterministic and auditable — a classical dissipative computation inspired by
open quantum-system dynamics, not a black-box model.

## 🦀 The contract (Stylus / Rust)

**v4, deployed live:** guardian sessions, approval registry with risk score, public
revocation status (`approval_status_pub` — the signing layer can read and enforce),
USDG escrow with challenge window (**real `IERC20.transferFrom` when a session token is
set**), dispute + guardian refund, emergency breaker. Typed errors (`TooRisky`,
`AboveDailyCap`, `NoSession`, `TokenTransferFailed`) and auditable events throughout.
Policy math is factored into pure functions covered by native unit tests (`cargo test`, 11/11).

Full cargo project: `zeus-guard-contract/` (stylus-sdk 0.10.9, v4 deployed size 22.5 KB).
The trust model — the engine is the advisor, the contract is the law — is in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```bash
# build & verify
cargo stylus check --endpoint https://sepolia-rollup.arbitrum.io/rpc
# deploy
cargo stylus deploy --endpoint https://sepolia-rollup.arbitrum.io/rpc --private-key <KEY>
```

## 🚀 Quickstart — verify the claims yourself

```bash
git clone https://github.com/clebson-scott/zeus-guard && cd zeus-guard
python3 engine/demo.py                  # expect: 40/40, ~1-2 ms/tx
cd zeus-guard-contract && cargo test    # expect: 11/11 native Rust policy tests
cd .. && python3 engine/honesty_experiment.py    # quench vs argmin, 1,850 cases
python3 proof/live_attack_defense.py --rpc https://sepolia-rollup.arbitrum.io/rpc \
    --contract 0xa9ef4e9be0e8f45e737f361380743faab72fe76a \
    --victim 0xf92721394140c43C72FbfF2f0ebf90327fD2bF9D   # 4/4 PASS, live contract
python3 engine/real_features.py --rpc https://arb1.arbitrum.io/rpc \
    --user 0xf92721394140c43C72FbfF2f0ebf90327fD2bF9D --to 0x912CE59144191C1204E64559FE8253a0e49E6548 --data 0xa9059cbb
# ^ screens a REAL mainnet address with features read from live chain state
```

Open [`demo/index.html`](demo/index.html) in any browser and click the four transaction
buttons — the verdicts (CLEARED / `TooRisky` / `AboveDailyCap` / `NoSession`) come live
from the deployed contract on Arbitrum Sepolia. No wallet, no setup.

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
├── zeus-guard-contract/         # THE contract — full cargo project (deployed as-is, cargo test)
├── demo/index.html              # live web demo: click a tx, verdict comes from the chain
├── demo/wallet.html              # retail wallet mock (guardian plugged in)
├── engine/qcsn_risk_engine.py   # dissipative risk engine
├── engine/demo.py               # benchmark: 40/40, 0.9-1.7 ms/tx
├── engine/real_features.py      # REAL chain screening: 8 features read from live RPC state
├── engine/honesty_experiment.py  # quench vs argmin, 1,850 cases, 0 divergences
├── proof/live_attack_defense.py # live attack & defense proof against the deployed contract
├── deploy/DEPLOYADO_V2_ARBITRUM_SEPOLIA.md      # v2 receipts: hashes, gas, smoke
├── deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md  # v1 receipts: hashes, gas, pipeline
├── docs/JUDGE_VERIFICATION.md   # 5-minute verification guide
├── docs/ARCHITECTURE.md         # trust model: who runs what, threat table
├── docs/MATH.md                 # the dissipative quench, formally
├── docs/ZEUS_GUARD_explainer.mp4        # 3:05 demo video
├── docs/VIDEO_ROTEIRO.md                # video script (Animalex style)
├── docs/zgv_render.py                   # programmatic video renderer
├── proof/                                # live attack/defense proof scripts + receipts
├── engine/DEMO_GUARDA.py                # interactive CLI demo of the engine
└── LICENSE                      # MIT
```

## ⚖️ Honest limitations

- **v2 (deployed) let a drainer-scored payment into escrow** — `escrowPayment` ignored its `risk_x100` parameter. Found by adversarial review, proven by the proof script, **fixed in v3** (`TooRisky` now reverts at the money path). v3 source ships here; redeploy is pending a funded testnet key.
- The quench's verdict equals plain argmin in all 1,850 tested cases (see the honesty experiment). The mechanism contributes continuous confidence p* and a physics-grounded reading — not a different verdict. Declared openly.
- Synthetic benchmark dataset (declared above) — real-data training is post-hackathon work. `real_features.py` is the bridge: the 8 features now come from live chain state, but the archetypes remain hand-designed.
- Disputes in v2 froze payments forever; v3 adds a 3-day deadline (`DisputeExpired` / auto-release).
- The deployed contract is the reference policy engine; signature-level wallet integration (guardian inside the wallet's confirm screen) is the next milestone — read-only EIP-1193 screening is live in [`demo/wallet.html`](demo/wallet.html).
- Testnet-only today; no mainnet deployment until audits.

## 🔗 Links

- Landing page: https://telegra.ph/ZEUS-GUARD--Pre-Transaction-Firewall-for-Everyday-Traders-09-26
- Explorer (v2): https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a
- Explorer (v1, histórico): https://sepolia.arbiscan.io/address/0x313e9994f1e77f579e797c19e29250a9a782e3a5
- Demo video: `docs/ZEUS_GUARD_explainer.mp4`

> *"Most people look at a profession and see a ceiling. I look at all of them at once
> and see a bridge."* — and this bridge guards your money.

---
*Built with 100% free, honest infrastructure: PoW faucet → official bridge → Stylus deploy. Every satoshi of testnet gas is receipted in the deploy docs.*
