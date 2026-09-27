# 🏛️ Architecture — who runs what, and why the guardian cannot be bypassed

## The one-sentence version

**The QCSN risk engine is the advisor; the Stylus contract is the law.** Users install
their own guardian with an on-chain policy; drainers must defeat math on-chain, not
persuade a user off-chain.

## Layers

```
┌──────────────────────────────────────────────────────────────┐
│  USER'S AGENT (off-chain, user-controlled — the "advisor")    │
│  • QCSN dissipative risk engine (engine/qcsn_risk_engine.py)  │
│  • simulation + calldata analysis of the pending tx            │
│  • produces risk score 0–10000 (risk_x100)                    │
│  • submits verdict to the contract BEFORE the user signs      │
└──────────────────────┬───────────────────────────────────────┘
                       │ check_tx(user, amount, risk_x100)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  ZEUS GUARD CONTRACT (on-chain, Stylus/Rust — the "law")      │
│  • session policy: guardian address, challenge window, cap    │
│  • hard limits: RISK_BLOCK (≥6000), daily cap 24h rolling     │
│  • escrow: payments held through challenge window            │
│  • approval registry readable on-chain (approval_status_pub)  │
│  • emergency freeze; guardian revoke; dispute; refund         │
└──────────────────────────────────────────────────────────────┘
```

## Why this split is the right one

1. **On-chain rules are binding regardless of the engine.** The daily cap, the challenge
   window, the freeze, and the escrow are enforced by the contract. Even a compromised
   agent cannot move escrowed value during the window, exceed the cap, or unfreeze a
   session. The agent can only *tighten* (flag risk), never *loosen* what's on-chain.
2. **The engine is deterministic and auditable.** No black-box model: production uses
   the analytic path (argmin + exact Gibbs confidence over 5 attack archetypes, see
   `MATH.md`); the quench-style dissipative integration is provably equivalent and kept
   for research reproduction (`engine/honesty_experiment.py`). Same input, same verdict,
   every time.
3. **The engine is untrusted from the contract's perspective.** `check_tx` treats
   `risk_x100` as advisory input from *the user's own session* (owner or guardian
   address). A third party cannot score transactions for someone else's session; the
   session binds the guardian.

## Threat model (honest)

| Threat | Mitigated by | Residual |
|---|---|---|
| Drainer approval (unlimited allowance) | engine → `TooRisky` + `guardian_revoke`; v4: any wallet/agent reads `approval_status_pub` **before signing** — revoked spenders are blocked at the signing layer | engine must see the tx first (agent integration) |
| Address poisoning | archetype in engine | same as above |
| Agent compromised | daily cap on-chain, challenge window, freeze, dispute/refund | cap funds at risk until freeze |
| User signs elsewhere (bypasses agent) | on-chain policy still binds everything routed through ZEUS (escrow, cap, freeze); v4 registry lets compliant wallets refuse revoked spenders | honest gap for non-ZEUS paths — roadmap: wallet-level RPC interception |
| Contract bug | testnet-only, unaudited, typed errors, MIT | audit before mainnet |

## Agentic payments (x402 / MPP)

For agent-initiated payments (the Robinhood Chain retail future), the agent does not
hold keys. It proposes; the contract's escrow holds the value through the challenge
window; the guardian can `dispute_payment` and `refund_disputed`. This is the policy
layer that makes "agent pays for you" safe for a non-technical user.

## USDG integration (Paxos)

`set_usdg_token(token)` switches a session to **real escrow**: `escrow_payment` pulls
the actual USDG via `IERC20.transferFrom` into the contract; `release_payment` pays the
payee; `refund_disputed` returns funds to the payer. With `address(0)` the session runs
in **ledger mode** (identical logic, no token movement — used by the on-chain receipts).

## What is NOT here yet (roadmap, declared)

- Wallet-side RPC interception so every signed tx necessarily passes the agent.
- Real-data training of the risk model (benchmark is synthetic, declared).
- Dune dashboard rendering blocked-threat telemetry (events are already emitted for it).


---

## 🔑 Who computes the risk? (the trust model, stated plainly)

The one question a careful judge asks: **`check_tx` receives `risk_x100` ready-made — who computes it, and why trust it?**

**The split: the agent judges, the contract enforces.**

| Layer | What it computes | Why you can trust it |
|---|---|---|
| Guardian agent (off-chain) | The QCSN risk score (`risk_x100`) from tx features | Deterministic and auditable: nearest-archetype selection over squared costs with exact Gibbs confidence, no black-box model. Same input → same score. Source: `engine/qcsn_risk_engine.py`, benchmark 40/40 at <0.1 ms/tx (quench-equivalent, see `engine/honesty_experiment.py`). |
| ZEUS GUARD contract (on-chain) | The **policy envelope**: 60% risk threshold, 24h rolling daily cap, session freeze, escrow challenge window | Trustless: the agent **cannot** override it. Even a malicious/compromised agent is capped — it can only block too much, never allow too much. |

**Why this design is safe even if the agent is wrong or hostile:**

1. **The contract is the last word.** A bad score can only make it *stricter* (false positives cost convenience, not money). The agent has no path to authorize value movement above the cap, past the freeze, or out of a disputed escrow.
2. **The user owns the policy.** `update_policy` (owner-only) sets the cap and the challenge window. The guardian can tighten enforcement but never loosen the owner's own limits.
3. **Value can't move in the same block.** `escrow_payment` holds USDG through a minimum 120s challenge window (`MIN_CHALLENGE_WINDOW`); `dispute_payment` + `refund_disputed` return funds to the payer even if everything else fails.
4. **Fail-closed by construction.** `check_tx` reverts on `SessionFrozen`, `TooRisky`, `AboveDailyCap`, `NoSession` — there is no "default allow" path.
5. **The mirror is verifiable.** Any wallet can re-run the same deterministic scorer locally and compare scores — the demo (`demo/wallet.html`) does exactly this and then confirms the verdict against the live contract.

**Honest limitation:** the risk *score* itself is a trusted input to the policy envelope. A future milestone is moving feature extraction on-chain (calldata-pattern rules in Rust) so that even the score is verifiable by third parties. Declared, not hidden.
