# ⚡ ZEUS GUARD — Pre-Transaction Firewall for Everyday Traders & Agentic Payments

> **The On-Chain Antivirus for Retail Web3 & Autonomous Agents:** A pre-transaction firewall operating at the EIP-1193 provider layer that intercepts drainers **before signature creation**, paired with a public revocation registry (`approval_status_pub`), a USDG escrow vault with a configurable challenge window (≥120s), and an emergency circuit-breaker — powered by a **sub-millisecond deterministic risk engine** — a fully deterministic argmin classifier in production, with no probabilistic or quantum-executed components (research origin in quantum spin networks is documented, not invoked at runtime).
>
> **Zero mystery math, zero quantum washing:** Production runs a deterministic, open-benchmark argmin classifier (<0.1 ms/tx) proven 100% equivalent (0 divergences across 1,848 test cases) to the dissipative quantum quench model.

**Author:** Clebson Campos de Araújo (Clebson Scott) · Arbitrum Open House Singapore 2026 · Buildathon
**Repo:** https://github.com/clebson-scott/zeus-guard · **Landing:** https://telegra.ph/ZEUS-GUARD--Pre-Transaction-Firewall-for-Everyday-Traders-09-26

---

## 🎯 TL;DR — Verified Status & Release Metrics (v6 hardened — canonical; v4 = audit-frozen RC powering the live web demos)

| Component | Status & Verified Metrics | Evidence / Artifact |
|---|---|---|
| **Deployed Stylus Contract (v6 hardened — CANONICAL)** | Active on Arbitrum Sepolia (`421614`) · Oracle multisig 2-of-3 in the money path · Live red-team proof **10 PASS / 0 FAIL** · Cached in ArbOS · WASM **32.0 KiB** | [`0x9b7608536a9704e120f0fc2c6722e2abb0fef848`](https://sepolia.arbiscan.io/address/0x9b7608536a9704e120f0fc2c6722e2abb0fef848) |
| **Deployed Stylus Contract (v6 — ROBINHOOD CHAIN TESTNET)** | Active on Robinhood Chain Testnet (`46630`) — the reserved-prize network · Same hardened code as canonical · Oracle multisig 2-of-3 · On-chain smoke test **PASS** | [`0xe18332679dc0bcfd1dda9e2e022252cbadb65eb5`](https://explorer.testnet.chain.robinhood.com/address/0xe18332679dc0bcfd1dda9e2e022252cbadb65eb5) · [deploy doc](deploy/DEPLOYADO_ROBINHOOD_TESTNET.md) |
| **Live Demo Contract (v4)** | Active on Arbitrum Sepolia (`421614`) · WASM Size: **23.4 KiB** — powers the web demos below | [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a) |
| **Native Rust Unit Tests** | **15/15 PASS** (vault auth, token restriction, 24h rolling cap restoration, reentrancy guard, session frozen check, dispute deadline, typed `AmountTooLarge`) | `cd zeus-guard-contract && cargo test` |
| **MV3 Extension & EIP-1193 Hook** | **10/10 PASS** (pre-installation injection at `document_start`, EIP-712 permit verification, pre-wallet 4001 cancelation error, `FAIL_OPEN` & `FAIL_CLOSED` fallback modes) | `node ext/test_extension.js` |
| **QCSN Engine & Honesty Experiment** | **0 quench vs argmin divergences** across **1,848 test cases**; analytic argmin latency **<0.1 ms/tx** | `python3 engine/honesty_experiment.py` |
| **Real Mainnet Data Benchmark** | **81 real Arbitrum events**: **100.0% Recall** (14/14 drainer attacks caught), **11.9% FP Rate** (down from 89.6% baseline), **90.1% Global Accuracy** | `python3 engine/realdata_benchmark.py` |
| **On-Chain Smoke Tests (v4)** | **13/13 PASS** on Arbitrum Sepolia | `python3 proof/smoke_v4.py` |
| **Live Attack & Defense Proof** | **4/4 PASS** on-chain against live contract | `python3 proof/live_attack_defense.py` |
| **INV9 Receiver-Match (phishing por intents)** | **33/33 PASS** — PASS/ALERT/INDETERMINADO honesto; camada request autoritativa + decoders calldata verificados (Across V3); calldata de intents é cego (receiver = keccak256(receiver‖sal)) | `python3 engine/test_inv9.py` |
| **Identity Layer & Ground Truth Correction (v4.5)** | 473/527 v2 "attacks" were verified protocol spends (Curve, Uniswap, 1inch...) — GT corrected by exclusion: **54 true attacks, recall 100% [93.4%, 100%] preserved**, FP **14.4% → 12.6%** with identity ON; label cache = 567 spenders (Blockscout, no API key) | `python3 engine/realdata_benchmark_gt_corrected.py` |
| **Temporal Split Validation** | Recall **100% in both halves** (25/25, 29/29); FP 18.0% → 10.7% across halves = causal token-freq warm-up artifact, documented | `python3 engine/realdata_benchmark_temporal.py` |
| **CI Automation** | Automated pipeline covering Stylus Rust (15/15), Python engine, and Node extension QA | `.github/workflows/ci.yml` |
| **Audit Package** | Complete audit package ready for external review | [`RELEASE_INDEX.md`](docs/RELEASE_INDEX.md) · [`JUDGE_SUBMISSION.md`](JUDGE_SUBMISSION.md) · [`docs/AUDIT_CHECKLIST.md`](docs/AUDIT_CHECKLIST.md) · [`SECURITY.md`](SECURITY.md) · [`REAL_DATA.md`](REAL_DATA.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/MATH.md`](docs/MATH.md) |

---

## 💡 The Core Problem: Why Web3 Security Fails Retail Users

Retail Web3 users and autonomous agents lose millions to drainer signatures, malicious ERC-20 approvals (`approve(spender, max)`), and stealth EIP-712 permits (`permit(...)`). The root causes are structural:

1. **Blind Signing:** Wallet UIs present raw hex or unverified contract addresses. Non-technical users cannot assess whether a spender is a legitimate DEX or a malicious drainer.
2. **Post-Signing Immutability:** Once a user signs a transaction or permit, execution is instantaneous on-chain. Post-facto security alerts, block explorers, and analytics can only log the theft after funds are gone.
3. **Approval Toxicity:** ERC-20 approvals granting unlimited allowances remain open indefinitely, allowing drainers to sweep funds months after the initial interaction.

---

## 🛡️ Pre-Wallet Defense: Why Defense Must Happen BEFORE the Wallet

Unlike traditional security tools that simulate transactions *after* the wallet modal opens or issue post-facto alerts, **ZEUS GUARD operates before signature creation**:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ 1. dApp Request (eth_sendTransaction / eth_signTypedData / permit)                │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ 2. EIP-1193 Pre-Wallet Extension Hook (ext/zeus_hook.js @ document_start)       │
│    • Intercepts RPC request BEFORE MetaMask / Rabby / Wallet modal opens         │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│ 3a. QCSN Risk Engine (<0.1 ms/tx)     │ │ 3b. On-Chain Status Check             │
│     • Feature vector x ∈ [0,1]⁸       │ │     • Queries Stylus Contract v4      │
│     • Nearest-archetype cost & Gibbs  │ │       approval_status_pub(user,     │
│     • Verdict: LIBERAR/ALERTAR/BLOQUEAR│ │       spender)                        │
└───────────────────┬───────────────────┘ └───────────────────┬───────────────────┘
                    │                                         │
                    └────────────────────┬────────────────────┘
                                         │
               ┌─────────────────────────┴─────────────────────────┐
               │ Risk Score ≥ 6000 OR Spender Revoked OR Over Cap? │
               └────────────┬─────────────────────────┬────────────┘
                            │ YES                     │ NO
                            ▼                         ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│ 🛑 REJECT AT PROVIDER LAYER           │ │ 🟢 FORWARD TO WALLET                  │
│    • Throws EIP-1193 Error Code 4001 │ │    • Wallet prompt opens normally     │
│    • Wallet modal NEVER opens         │ │    • User signs legitimate tx         │
│    • NO signature ever created        │ │    • Enters USDG Escrow Vault if applicable│
└───────────────────────────────────────┘ └───────────────────────────────────────┘
```

By intercepting at the provider level (`window.ethereum`), ZEUS GUARD prevents signature creation entirely when an attack or revoked approval is detected, throwing standard EIP-1193 cancelation code `4001`.

---

## ⚡ Why This Is Different (Por que isso é diferente)

*Honest engineering distinctions without marketing hyperbole:*

1. **Pre-Signing Hook vs. Post-Signing Alerts:** Intercepts RPC requests at the `EIP-1193` provider layer at `document_start`. It prevents signature creation before the wallet modal ever opens, rather than warning after the user clicks or logging after funds are drained.
2. **On-Chain Policy Engine vs. Off-Chain Black Box:** Off-chain scoring is advisory; the Arbitrum Stylus WASM smart contract (`0xa9ef...`) is the un-bypassable law on-chain enforcing a 60% risk limit, daily rolling 24h cap, session freezing, public revocation registry (`approval_status_pub`), and a USDG escrow challenge window (≥120s).
3. **Transparent Math & Zero Quantum Washing:** The risk classifier was originally conceived using Quantum Continuous Spin Network (QCSN) dissipative quench protocols. To achieve sub-millisecond RPC latency (<0.1 ms/tx), production uses an exact, deterministic analytical argmin solver. We proved 0 quench vs. argmin divergences in 1,848 test cases (`engine/honesty_experiment.py`) and keep quantum hardware validation (`ibm_fez`) as open research while serving hyper-fast, audited CPU code in production.
4. **Empirical Mainnet Grounding:** Tested against 81 real Arbitrum Mainnet `Approve` events (100.0% recall on drainer attacks, 11.9% false positive rate down from 89.6% baseline) with strict zero-future-leakage temporal causality (`block <= tx.block`).

---

## 🏛️ System Architecture & On-Chain Enforcement Layer

| Module | Purpose | Enforcement Layer |
|---|---|---|
| **Pre-Transaction Firewall** | Screens every transaction & permit before signing; blocks drainers (`TooRisky`) and cap violations (`AboveDailyCap`). | MV3 Extension (`zeus_hook.js`) & Stylus Contract (`check_tx`) |
| **Public Revocation Registry (`approval_status_pub`)** | Exposes on-chain approval status and revocation state for wallets and dApps before signing. | Stylus Contract v4 & EIP-712 Hook |
| **USDG Escrow Vault** | Intercepts agentic / retail payments via real `IERC20.transferFrom` and holds them through a challenge window (≥120s). | Stylus Contract (`escrow_payment` / `vault_send`) |
| **Dispute & Guardian Refund** | Allows guardian to dispute suspicious transactions and issue refunds (`refund_disputed`) restoring active rolling cap. | Stylus Contract (`dispute_payment` / `refund_disputed`) |
| **Emergency Circuit-Breaker** | Freezes session state (`session_frozen`) blocking all contract mutations on attack detection. | Stylus Contract (`freeze_session`) |

### The Real Role of On-Chain (Arbitrum Stylus WASM v4)

The smart contract is not a passive event logger; it is the **immutable policy state machine**:
- **`check_tx(user, amount, risk_x100)`**: Validates risk score against `RISK_BLOCK_X100` (6000 = 60%), verifies session state, checks active daily rolling 24h allowance (`current_daily_spent`), and reverts on violation (`TooRisky`, `AboveDailyCap`, `SessionFrozen`, `NoSession`).
- **`approval_status_pub(user, spender)`**: Public state mapping readable by any extension or dApp to check if a spender has been flagged or revoked (`guardian_revoke`).
- **`escrow_payment` & `vault_send`**: Pulls actual USDG ERC-20 tokens via `IERC20.transferFrom` and holds custody for at least 120 seconds (`MIN_CHALLENGE_WINDOW`).
- **`dispute_payment` & `refund_disputed`**: Enables the guardian to challenge suspicious transfers within the window and refund tokens back to the user, safely restoring the 24h rolling cap (`restore_daily_spent`).

---

## ⚛️ The QCSN Risk Engine: Quantum Research Origin & Production Scorer

### Research Origin vs. Production Analytical Engine
1. **Research Origin (Quantum Continuous Spin Network):** The classifier models decision boundaries as continuous spin dynamics under a thermal bath dissipative quench (60-step annealing, β: 2→40). The mechanism was experimentally measured on superconducting QPU **IBM Quantum `ibm_fez`** (job `daorvfg2fm4c73f5tlog`, selection fidelity 0.997).
2. **Production Engine (Analytical Argmin Path):** For sub-millisecond tx-time interception (<0.1 ms/tx), production computes the decision via exact nearest-archetype selection (argmin over squared feature distance) with exact Gibbs probability distribution at β = 40.
3. **The Equivalence Proof (`engine/honesty_experiment.py`):**
   - Tested 1,848 test cases across synthetic benchmarks, stress noise (σ = 0.05, 0.15, 0.30), and exact midpoints.
   - Result: **0 quench vs. argmin divergences**. The dissipative quench anneals to the exact same decision as argmin at 276x higher compute cost. Production uses the fast CPU argmin path honestly and transparently.

### Real Mainnet Data Benchmark (`python3 engine/realdata_benchmark.py`)

- **Dataset:** 81 real `Approve` events collected from Arbitrum Mainnet, labeled strictly by on-chain outcome with zero future leakage (`block <= tx.block`).
- **Drainer Attacks Captured (Recall):** **14/14 (100.0% Recall)** — 10 direct `BLOQUEAR`, 4 preventive `ALERTAR`.
- **False Positive Rate:** **11.9% (8/67 benign)**, compared to **89.6%** in standard unguided "unlimited allowance / EOA" baselines.
- **Global Accuracy:** **90.1% (73/81 correctly classified)**.

---

## 📊 Verified Metrics & Explicit Limitations

### Verified Metrics Matrix
- **Contract Size:** 23.4 KiB WASM compiled via Rust Stylus (`cargo stylus check`).
- **Unit Test Coverage:** 15/15 Rust unit tests passing (`cargo test`).
- **Extension QA:** 10/10 Node.js extension tests passing (`node ext/test_extension.js`).
- **On-Chain Smoke Tests:** 13/13 passing on Arbitrum Sepolia (`python3 proof/smoke_v4.py`).
- **Live Attack & Defense:** 4/4 passing on-chain against live contract (`python3 proof/live_attack_defense.py`).

### Verified Limitations (Declared & Transparent)
1. **False Positive Rate (11.9%):** 8 out of 67 benign approvals (e.g., brand-new legitimate contracts or unverified DEX routers) were flagged as risky (`ALERTAR`). This is an intentional tradeoff prioritizing 100% drainer recall over unguided permissive access.
2. **Escrow Latency (≥120s Challenge Window):** The escrow vault introduces a minimum 120-second delay before payment release. This design is optimized for retail transfers, subscription payments, and agentic settlements, not high-frequency trading (HFT) or flash loans.
3. **Extension Fallback Modes:** When the off-chain scorer RPC is unreachable, the extension operates in `FAIL_OPEN` (warns user, allows signature) by default, or `FAIL_CLOSED` (blocks with 4001) if strict security mode is selected.
4. **Quantum Path Role:** Quantum QPU execution is an open research origin and validation benchmark, not an active cloud endpoint in the live transaction path.

---

## 🚀 Quickstart & Verification Commands

```bash
# 1. Run Native Contract Unit Tests (15/15 PASS)
cd zeus-guard-contract && cargo test

# 2. Check Stylus WASM Compilation (23.4 KiB)
cargo stylus check

# 3. Run QCSN Synthetic Benchmark & Honesty Experiment (0 divergences)
python3 engine/demo.py
python3 engine/honesty_experiment.py

# 4. Run Real Data Mainnet Benchmark (100% Recall, 11.9% FP)
python3 engine/realdata_benchmark.py

# 5. Run Extension MV3 QA Test Harness (10/10 PASS)
node ext/test_extension.js

# 6. Run On-Chain Smoke Tests v4 (13/13 PASS)
python3 proof/smoke_v4.py

# 7. Run Live Attack & Defense Proof (4/4 PASS)
python3 proof/live_attack_defense.py --rpc https://sepolia-rollup.arbitrum.io/rpc   --contract 0xa9ef4e9be0e8f45e737f361380743faab72fe76a   --victim 0x1718bd9000B81bD5996DeE981eb76232bc2438B3
```

---

## 🚦 Final Release Readiness Report

1. **Ready Now on Testnet (Arbitrum Sepolia):**
   - Stylus v4 contract deployed and active at [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a).
   - All test suites passing (15/15 Rust unit, 10/10 Node extension, 13/13 on-chain smoke, 4/4 live defense, 0 engine divergences).
2. **Ready for External Audit:**
   - Complete audit package compiled in `docs/AUDIT_CHECKLIST.md`, `SECURITY.md`, `REAL_DATA.md`, `docs/ARCHITECTURE.md`, and `docs/MATH.md`.
3. **Blocked for Mainnet:**
   - Mainnet deployment is **strictly blocked** pending formal external audit by a specialized smart contract security firm and production private key / multisig setup.
