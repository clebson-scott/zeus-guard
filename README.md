# ⚡ ZEUS GUARD — The Pre-Transaction Firewall for Everyday Traders

> The on-chain antivirus for retail users: a pre-transaction firewall with revocation of
> poisoned approvals, a USDG escrow vault with a challenge window, and an emergency
> circuit-breaker — powered by a **fast, deterministic risk engine** (with a quench-style
> dissipative selector whose quantum-hardware validation we keep as open research).
> No mystery math: the production engine is a measured argmin, benchmarked in the open.

**Author:** Clebson Campos de Araújo (Clebson Scott) · Arbitrum Open House Singapore 2026 · Buildathon
**Repo:** https://github.com/clebson-scott/zeus-guard · **Landing:** https://telegra.ph/ZEUS-GUARD--Pre-Transaction-Firewall-for-Everyday-Traders-09-26

---

## 🎯 TL;DR — What's Live Right Now (v4 Release Candidate)

| Component | Status & Evidences |
|---|---|
| **Deployed Stylus Contract (v4)** | [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a) on Arbitrum Sepolia (Chain ID 421614) · WASM Size: 23.4 KiB |
| **Native Rust Policy Tests** | `cd zeus-guard-contract && cargo test` — **15/15 tests passing** (vault auth, token restriction, 24h rolling cap restoration, reentrancy guard, session frozen check, dispute deadline, typed `AmountTooLarge`) |
| **QCSN Engine & Honesty Experiment** | `python3 engine/honesty_experiment.py` — **0 quench vs argmin divergences in 1,863 test cases**; analytic argmin latency **<0.1 ms/tx** |
| **Real Mainnet Data Benchmark** | `python3 engine/realdata_benchmark.py` — **81 real Arbitrum events**: **100.0% Recall** (14/14 drainer attacks caught), **11.9% FP Rate** (down from 89.6% baseline), **90.1% Global Accuracy** |
| **MV3 Extension & EIP-1193 Hook** | `node ext/test_extension.js` — **7/7 tests passing** (pre-installation hook, EIP-712 permit verification via `approval_status_pub`, EIP-1193 4001 cancelation error, `FAIL_OPEN` & `FAIL_CLOSED` modes) |
| **On-Chain Smoke Tests (v4)** | `python3 proof/smoke_v4.py` — **13/13 passing on-chain** |
| **Live Attack & Defense Proof** | `python3 proof/live_attack_defense.py --rpc ... --contract 0xa9ef... --victim ...` — **4/4 passing on-chain** against live contract |
| **CI Automation** | `.github/workflows/ci.yml` — Automated testing across Rust Stylus contract (15/15), Python risk engine & benchmarks, and Node extension QA |
| **Audit Package** | [`docs/AUDIT_CHECKLIST.md`](docs/AUDIT_CHECKLIST.md) · [`SECURITY.md`](SECURITY.md) · [`REAL_DATA.md`](REAL_DATA.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/MATH.md`](docs/MATH.md) |

---

## 🛡️ The Product Architecture

| Module | Purpose | Enforcement Layer |
|---|---|---|
| **Pre-Transaction Firewall** | Screens every transaction & permit before signing; blocks drainers (`TooRisky`) and cap violations (`AboveDailyCap`). | MV3 Extension (`zeus_hook.js`) & Stylus Contract (`check_tx`) |
| **Public Revocation Registry (`approval_status_pub`)** | Exposes on-chain approval status and revocation state for wallets and dApps before signing. | Stylus Contract v4 & EIP-712 Hook |
| **USDG Escrow Vault** | Intercepts agentic / retail payments via real `IERC20.transferFrom` and holds them through a challenge window (≥120s). | Stylus Contract (`escrow_payment` / `vault_send`) |
| **Dispute & Guardian Refund** | Allows guardian to dispute suspicious transactions and issue refunds (`refund_disputed`) restoring active rolling cap. | Stylus Contract (`dispute_payment` / `refund_disputed`) |
| **Emergency Circuit-Breaker** | Freezes session state (`session_frozen`) blocking all contract mutations on attack detection. | Stylus Contract (`freeze_session`) |

---

## ⚛️ The QCSN Risk Engine: Honest & Deterministic

The risk classifier computes **nearest-archetype selection over squared feature distances** (argmin) with an exact Gibbs probability distribution. A 60-step dissipative quench (β: 2→40) was tested and proved mathematically equivalent across 1,863 test cases (`python3 engine/honesty_experiment.py` — 0 divergences). Production uses the fast, deterministic argmin path (<0.1 ms/tx).

### Real Data Benchmark Summary (`python3 engine/realdata_benchmark.py`)

- **Dataset:** 81 real `Approve` events collected from Arbitrum Mainnet, labeled strictly by on-chain outcome with zero future leakage (`block <= tx.block`).
- **Ataques (Drainers):** 14/14 captured (**100.0% Recall**).
- **False Positive Rate:** **11.9%** (8/67 benign), compared to **89.6%** in standard "unlimited allowance / EOA" baseline.
- **Overall Accuracy:** **90.1%** (73/81 correctly classified).

---

## 🦀 Smart Contract (Stylus / Rust v4)

- **Deployed Address:** [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a)
- **Chain ID:** Arbitrum Sepolia (`421614`)
- **Key Safety Features:**
  - `is_vault_authorized` enforcing owner/guardian access in `vault_send`.
  - `is_token_allowed` restricting custody strictly to registered USDG token (`session_usdg`).
  - `ReentrancyGuard` active on all external ERC-20 token interactions.
  - 24h rolling cap accounting with safe restoration (`restore_daily_spent`).
  - Strict input sanitization avoiding panics (`amount_fits_u128`, `risk_saturating`, `u64_saturating`).

---

## 🚀 Quickstart & Verification Commands

```bash
# 1. Run Native Contract Unit Tests (15/15 PASS)
cd zeus-guard-contract && cargo test

# 2. Check Stylus WASM Compilation (23.4 KiB)
cargo stylus check

# 3. Run QCSN Engine Synthetic Benchmark & Honesty Experiment
python3 engine/demo.py
python3 engine/honesty_experiment.py

# 4. Run Real Data Benchmark (100% Recall, 11.9% FP)
python3 engine/realdata_benchmark.py

# 5. Run Extension MV3 QA Test Harness (7/7 PASS)
node ext/test_extension.js

# 6. Run On-Chain Smoke Tests v4
python3 proof/smoke_v4.py

# 7. Run Live Attack & Defense Proof
python3 proof/live_attack_defense.py --rpc https://sepolia-rollup.arbitrum.io/rpc \
  --contract 0xa9ef4e9be0e8f45e737f361380743faab72fe76a \
  --victim 0x1718bd9000B81bD5996DeE981eb76232bc2438B3
```

---

## 🚦 Final Release Readiness Report

1. **Ready Now on Testnet (Arbitrum Sepolia):**
   - Stylus v4 contract deployed and active at `0xa9ef4e9be0e8f45e737f361380743faab72fe76a`.
   - All test suites passing (15/15 Rust unit, 7/7 Node extension, 13/13 on-chain smoke, 4/4 live defense, 0 engine divergences).
2. **Ready for External Audit:**
   - Complete audit package compiled in `docs/AUDIT_CHECKLIST.md`, `SECURITY.md`, `REAL_DATA.md`, `ARCHITECTURE.md`, and `MATH.md`.
3. **Blocked for Mainnet:**
   - Mainnet deployment is **strictly blocked** pending formal external audit by a specialized smart contract security firm and production private key / multisig setup.
