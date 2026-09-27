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
LATENCIA MEDIA:  0.9 ms/tx (quench completo de 60 passos)
```

The engine is ~150 lines of pure Python (`engine/qcsn_risk_engine.py`): a Gibbs quench
(β 2→40, 60 steps) over 5 attack-archetype branches. Deterministic, no RNG, no black box.
The quantum-hardware validation (IBM `ibm_fez`, job `daorvfg2fm4c73f5tlog`, selection
fidelity 0.997) is documented in the README.

## 2. Verify the live contract (2 min, no wallet)

**v2 (current, real USDG escrow) — open the explorer:**
https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a

- **v2 contract**: Rust/Stylus, 21.9 KB, activated 26/09/2026 (stylus-sdk 0.10.9, Rust 1.98.1).
- **v2 deploy tx (initcode)**: [0x0227ef40a5b9d199e3eff80c9630879fdf90b2798beb32665fa3338b4d06e672](https://sepolia.arbiscan.io/tx/0x0227ef40a5b9d199e3eff80c9630879fdf90b2798beb32665fa3338b4d06e672)
- **v2 activation tx**: [0x2e658e8abb37549d42671da8970bc3b06f053c2c83bc2d03ed72c00033f51978](https://sepolia.arbiscan.io/tx/0x2e658e8abb37549d42671da8970bc3b06f053c2c83bc2d03ed72c00033f51978)
- **v2 ArbOS cache bid**: [0xa6f19477c67b6209b167c183a21bd9e141dd47023d4acccb2e6b01e76f5797e2](https://sepolia.arbiscan.io/tx/0xa6f19477c67b6209b167c183a21bd9e141dd47023d4acccb2e6b01e76f5797e2)
- **v2 demo session init**: [0x8cc71c04e82ca8d0247a541d6669b2a3c44be8377b64ec01229293301c854ead](https://sepolia.arbiscan.io/tx/0x8cc71c04e82ca8d0247a541d6669b2a3c44be8377b64ec01229293301c854ead)
- **Live web demo**: open [`demo/index.html`](../demo/index.html) in a browser — every button queries this contract, no wallet.

v1 (original, historical receipts): [0x313e9994f1e77f579e797c19e29250a9a782e3a5](https://sepolia.arbiscan.io/address/0x313e9994f1e77f579e797c19e29250a9a782e3a5)
- v1 activation: [0x1e3515c1d6d9565fc12e0f4c2ae311ee77868131b23666a06de7d9f01773fe59](https://sepolia.arbiscan.io/tx/0x1e3515c1d6d9565fc12e0f4c2ae311ee77868131b23666a06de7d9f01773fe59) · deploy: [0xc893dbc4c59a1fd11abf054f1c4c81a6054b4da187df700a3f41e6a41c1fcfcb](https://sepolia.arbiscan.io/tx/0xc893dbc4c59a1fd11abf054f1c4c81a6054b4da187df700a3f41e6a41c1fcfcb) · cache bid: [0xe51c05312b723a818aa3d3c08009f0e8210be856a66510820ae8bf459dbdace6](https://sepolia.arbiscan.io/tx/0xe51c05312b723a818aa3d3c08009f0e8210be856a66510820ae8bf459dbdace6)

## 3. Replay the smoke tests (2 min, needs `cast` or any ABI-capable tool)

The contract's public interface (from `zeus-guard-contract/src/lib.rs`):

| Function | Signature | Role |
|---|---|---|
| `initSession` | `(guardian: address, challenge_window: u256, daily_cap: u256)` | starts a guardian session |
| `checkTx` | `(user: address, amount: u256, risk_x100: u256)` | the firewall verdict |
| `logApproval` | `(user, spender, amount, risk_x100)` | approval registry |
| `guardianRevoke` | `(user, spender)` | auto-revocation |
| `escrowPayment` | `(payment_id: bytes32, payee, amount, risk_x100)` | USDG vault entry |
| `disputePayment` / `releasePayment` | `(payment_id)` | challenge window |
| `emergencyFreeze` / `unfreeze` | `(user)` / `()` | circuit-breaker |

> **ABI note (honest gotcha, costs 10 minutes if you miss it):** the Stylus SDK exports
> Rust function names in **camelCase** — `sessionExists(address)`, not `session_exists`.
> Calling a snake_case selector reverts with empty data ("unknown method"). All names in
> this guide are the real, exported ones.

Smoke tests already executed on-chain (receipts: [`deploy/DEPLOYADO_V2_ARBITRUM_SEPOLIA.md`](../deploy/DEPLOYADO_V2_ARBITRUM_SEPOLIA.md) · [`deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md`](../deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md)):

| Test | Input | Result |
|---|---|---|
| Normal tx clears | risk 250 | ✅ allowed |
| Drainer blocked | risk 6000 ≥ RISK_BLOCK_X100 (6000) | ⛔ `TooRisky` (selector `0xcc65e730`) |
| Daily cap enforced | 0.6 ETH vs 0.5 cap | ⛔ `AboveDailyCap` (selector `0x73fede4c`) |
| Session required | no prior `initSession` | ⛔ `NoSession` (selector `0xaabbee68`) |
| Challenge window enforced | `releasePayment` right after `escrowPayment` | ⛔ `ChallengeWindowOpen` — re-run on v2, 26/09 |

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
`0xf92721394140c43C72FbfF2f0ebf90327fD2bF9D` on the explorer).

## 5. What to be skeptical about (we are too)

- The 40/40 benchmark uses a **synthetic** dataset — separable archetypes, no real-world
  noise. It proves the mechanism runs at tx speed, not production-grade detection.
- "Quantum-validated" refers to the **dissipative selection mechanism** (fidelity 0.997 on
  `ibm_fez`), not to the deployed contract running on a QPU.
- Wallet-side agent integration is not in this repo; the deployed contract is the policy
  engine that such an agent would call.

Questions? Open an issue in this repo — every answer will be receipted.
