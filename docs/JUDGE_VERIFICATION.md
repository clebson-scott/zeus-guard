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

Open the explorer:
https://sepolia.arbiscan.io/address/0x313e9994f1e77f579e797c19e29250a9a782e3a5

- **Contract tab**: Rust/Stylus contract, 19.2 KB, activated 23/09/2026.
- **ArbOS cache bid**: [0xe51c05312b723a818aa3d3c08009f0e8210be856a66510820ae8bf459dbdace6](https://sepolia.arbiscan.io/tx/0xe51c05312b723a818aa3d3c08009f0e8210be856a66510820ae8bf459dbdace6)
- **Activation tx**: [0x1e3515c1d6d9565fc12e0f4c2ae311ee77868131b23666a06de7d9f01773fe59](https://sepolia.arbiscan.io/tx/0x1e3515c1d6d9565fc12e0f4c2ae311ee77868131b23666a06de7d9f01773fe59)
- **Deploy tx (initcode)**: [0xc893dbc4c59a1fd11abf054f1c4c81a6054b4da187df700a3f41e6a41c1fcfcb](https://sepolia.arbiscan.io/tx/0xc893dbc4c59a1fd11abf054f1c4c81a6054b4da187df700a3f41e6a41c1fcfcb)

## 3. Replay the smoke tests (2 min, needs `cast` or any ABI-capable tool)

The contract's public interface (from `zeus-guard-contract/src/lib.rs`):

| Function | Signature | Role |
|---|---|---|
| `init_session` | `(guardian: address, challenge_window: u256, daily_cap: u256)` | starts a guardian session |
| `check_tx` | `(user: address, amount: u256, risk_x100: u256)` | the firewall verdict |
| `log_approval` | `(user, spender, amount, risk_x100)` | approval registry |
| `guardian_revoke` | `(user, spender)` | auto-revocation |
| `escrow_payment` | `(payment_id: bytes32, payee, amount, risk_x100)` | USDG vault entry |
| `dispute_payment` / `release_payment` | `(payment_id)` | challenge window |
| `emergency_freeze` / `unfreeze` | `(user)` / `()` | circuit-breaker |

Smoke tests already executed on-chain (receipts in [`deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md`](../deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md)):

| Test | Input | Result |
|---|---|---|
| Normal tx clears | risk 250 | ✅ allowed |
| Drainer blocked | risk 6000 ≥ RISK_BLOCK_X100 (6000) | ⛔ `TooRisky` (selector `0xcc65e730`) |
| Daily cap enforced | 0.6 ETH vs 0.5 cap | ⛔ `AboveDailyCap` (selector `0x73fede4c`) |
| Session required | no prior `init_session` | ⛔ `NoSession` (selector `0xaabbee68`) |

To replay with `cast` (any funded Arbitrum Sepolia key, e.g. from the public PoW faucet):

```bash
cast send 0x313e9994f1e77f579e797c19e29250a9a782e3a5 \
  "init_session(address,uint256,uint256)" \
  <GUARDIAN_ADDR> 3600 500000000000000000 \
  --rpc-url https://sepolia-rollup.arbitrum.io/rpc --private-key <KEY>

# expect revert TooRisky:
cast call 0x313e9994f1e77f579e797c19e29250a9a782e3a5 \
  "check_tx(address,uint256,uint256)" <USER_ADDR> 0 6000 \
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
