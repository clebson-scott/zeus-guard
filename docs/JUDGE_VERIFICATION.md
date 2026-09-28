# 🧪 JUDGE VERIFICATION GUIDE — ZEUS GUARD in ~5 minutes

Every claim in this repo is verifiable. Nothing here depends on trust.

## 1. Run the risk-engine benchmark (1 min, no wallet)

```bash
git clone https://github.com/clebson-scott/zeus-guard && cd zeus-guard
python3 engine/demo.py
```

**Expected output (tail):**
```
ACURACIA QCSN:   40/40 = 100.0%
ACURACIA LIMIAR: 38/40 = 95.0%
LATENCIA MEDIA:  0.0 ms/tx (caminho analitico: argmin + Gibbs exata)
```

The engine is ~150 lines of pure Python (`engine/qcsn_risk_engine.py`): a Gibbs quench
(β 2→40, 60 steps) over 5 attack-archetype branches. Deterministic, no RNG, no black box.
Production runs the fast analytic argmin path (<0.1 ms/tx); the quench-style dissipative
integration is provably equivalent (0 divergences across 1,848 test cases in `python3 engine/honesty_experiment.py`).
The quantum-hardware validation (IBM `ibm_fez`, job `daorvfg2fm4c73f5tlog`, selection
fidelity 0.997) is documented in the README.

## 2. Verify the live contract (2 min, no wallet)

**v4 (current, Stylus Release Candidate) — open the explorer:**
https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a

- **v4 contract**: Rust/Stylus, 23.4 KiB (23,939 bytes), activated 26/09/2026 (stylus-sdk 0.10.9, Rust 1.98.1).
- **v4 deploy tx (initcode)**: [`0xe87a27c6da339fa0258f3c8e0213fa71c97146cff18ee9a0e420a1fc467516a3`](https://sepolia.arbiscan.io/tx/0xe87a27c6da339fa0258f3c8e0213fa71c97146cff18ee9a0e420a1fc467516a3)
- **v4 activation tx**: [`0x878bf81b6100851f5789603b7ca795fae1a58d42542d79bdaf824d472c15a4d0`](https://sepolia.arbiscan.io/tx/0x878bf81b6100851f5789603b7ca795fae1a58d42542d79bdaf824d472c15a4d0)
- **Live web demo**: open [`demo/index.html`](../demo/index.html) in a browser — every button queries this contract, no wallet.

Historical releases: v3, v2, v1 (`0x313e9994f1e77f579e797c19e29250a9a782e3a5`).

## 3. Replay the smoke tests (2 min, needs `cast` or any ABI-capable tool)

The contract's public interface (from `zeus-guard-contract/src/lib.rs`):

| Function | Signature | Role |
|---|---|---|
| `initSession` | `(guardian: address, challenge_window: u256, daily_cap: u256)` | starts a guardian session |
| `checkTx` | `(user: address, amount: u256, risk_x100: u256)` | the firewall verdict |
| `logApproval` | `(user, spender, amount, risk_x100)` | approval registry |
| `approvalStatusPub` | `(user: address, spender: address)` | public approval & revocation status |
| `guardianRevoke` | `(user, spender)` | auto-revocation |
| `escrowPayment` | `(payment_id: bytes32, payee, amount, risk_x100)` | USDG vault entry |
| `disputePayment` / `releasePayment` | `(payment_id)` | challenge window |
| `refundDisputed` | `(payment_id)` | guardian refund |
| `emergencyFreeze` / `unfreeze` | `(user)` / `()` | circuit-breaker |

> **ABI note (honest gotcha, costs 10 minutes if you miss it):** the Stylus SDK exports
> Rust function names in **camelCase** — `sessionExists(address)`, not `session_exists`.
> Calling a snake_case selector reverts with empty data ("unknown method"). All names in
> this guide are the real, exported ones.

Smoke tests already executed on-chain (receipts: [`deploy/DEPLOYADO_V4_ARBITRUM_SEPOLIA.md`](../deploy/DEPLOYADO_V4_ARBITRUM_SEPOLIA.md)):

| Test | Input | Result |
|---|---|---|
| Normal tx clears | risk 250 | ✅ allowed |
| Drainer blocked | risk 6000 ≥ RISK_BLOCK_X100 (6000) | ⛔ `TooRisky` (selector `0xcc65e730`) |
| Daily cap enforced | 0.6 ETH vs 0.5 cap | ⛔ `AboveDailyCap` (selector `0x73fede4c`) |
| Session required | no prior `initSession` | ⛔ `NoSession` (selector `0xaabbee68`) |
| Challenge window enforced | `releasePayment` right after `escrowPayment` | ⛔ `PaymentDisputed` / `ChallengeWindowOpen` |

To replay with `cast` (any funded Arbitrum Sepolia key, e.g. from the public PoW faucet):

```bash
cast send 0xa9ef4e9be0e8f45e737f361380743faab72fe76a \
  "initSession(address,uint256,uint256)" \
  <GUARDIAN_ADDR> 3600 500000000000000000000 \
  --rpc-url https://sepolia-rollup.arbitrum.io/rpc --private-key <KEY>

# expect revert TooRisky:
cast call 0xa9ef4e9be0e8f45e737f361380743faab72fe76a \
  "checkTx(address,uint256,uint256)" <USER_ADDR> 0 6000 \
  --rpc-url https://sepolia-rollup.arbitrum.io/rpc
```

## 4. Funding pipeline (transparency)

The whole testnet war chest was built for free, with receipts:
1. PoW faucet (sepolia-faucet.pk910.de): honest mining → 0.064 SepETH
2. Official Arbitrum bridge `depositEth()` → 0.06 ETH on L2
3. `cargo stylus deploy` — contract + activation + smoke tests ≈ 0.005 ETH

Remaining L2 balance at submission time: ~0.059 ETH (public record: the deploy wallet
`0x1718bd9000B81bD5996DeE981eb76232bc2438B3` on the explorer).

## 5. What to be skeptical about (we are too)

- The 40/40 benchmark uses a **synthetic** dataset — separable archetypes, no real-world
  noise. It proves the mechanism runs at tx speed, not production-grade detection. Real data benchmark (`python3 engine/realdata_benchmark.py`) on 81 Arbitrum Mainnet events achieves 100% recall and 11.9% FP rate.
- "Quantum-validated" refers to the **dissipative selection mechanism** (fidelity 0.997 on
  `ibm_fez`), not to the deployed contract running on a QPU.
- Wallet-side agent integration is provided via MV3 extension (`ext/zeus_hook.js`); the deployed contract is the policy engine that such an agent/wallet calls.

Questions? Open an issue in this repo — every answer will be receipted.
