# ⚡ ZEUS GUARD v4 — DEPLOY OFICIAL NA ARBITRUM SEPOLIA

**Data:** 26/09/2026, ~22h35 UTC
**Rede:** Arbitrum Sepolia (chainId 421614)
**Contrato v4:** `0xa9ef4e9be0e8f45e737f361380743faab72fe76a`
**Explorer:** https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a
**Carteira deploy:** `0x1718bd9000B81bD5996DeE981eb76232bc2438B3` (testnet-only)
**Novidade v4:** `approval_status_pub(user, spender) -> (amount, risk_x100, revoked)` —
o registro de aprovações virou legível publicamente. Wallets, agentes e guardiões
consultam o registro **antes de assinar**: a revogação deixa de ser declarativa e
vira enforcement na camada de assinatura. (Para aprovações de EOA a chain não pode
revogar um allowance por terceiros — o modelo de confiança honesto está no
`docs/ARCHITECTURE.md`.)

## Transações do deploy
| Etapa | Hash |
|---|---|
| Deploy (initcode) | `0xe87a27c6da339fa0258f3c8e0213fa71c97146cff18ee9a0e420a1fc467516a3` |
| Ativação Stylus (instância #1) | `0x878bf81b6100851f5789603b7ca795fae1a58d42542d79bdaf824d472c15a4d0` |
| Ativação Stylus (instância canônica deste registro) | segunda execução do mesmo initcode; endereço acima |

**Metadados:** wasm 22,5 KiB (23.031 bytes), data fee 0,000143 ETH,
toolchain stylus 0.6.3, stylus-sdk 0.10.9, `cargo stylus deploy --no-verify`.

## Smoke v4 on-chain: 21/21 passou
Política: initSession ✅ · risk 90% ⛔ TooRisky · risk 59,99% ✅ passa ·
escrow em risco ⛔ TooRisky · 2^130 wei ⛔ AmountTooLarge (tipado).

**Loop de revogação fechado (novo em v4):**
- `logApproval(spender, 1e18, risk=1)` ✅
- `approval_status_pub` → `(amount=1e18, risk=100, revoked=false)` ✅ legível publicamente
- `guardianRevoke` ✅ → `approval_status_pub` → **`revoked=true`** ✅
- A camada de assinatura consulta e recusa: enforcement real.

**Cofre real com ERC-20 (MockUSDG `0x96Fa5CeA89e749e30686084A1bE522EC7d12Dab9`):**
approve ✅ · setUsdgToken ✅ · escrowPayment retém 10 mUSDG ✅ ·
disputePayment ✅ · release ⛔ PaymentDisputed · refundDisputed devolve integral ✅ ·
teardown setUsdgToken(0) ✅.

**Circuito de emergência:** emergencyFreeze ✅ → frozen=true ✅ · unfreeze ✅.

## Motor de risco v4 (off-chain)
`engine/qcsn_risk_engine.py`: produção agora usa o **caminho analítico**
(argmin + probabilidade de Gibbs exata) — veredito idêntico ao quench (0 divergências
comprovadas em `engine/honesty_experiment.py`), ~1000x mais rápido (<0,1 ms/tx).
O quench numérico fica como `classify_quench()` para reprodução da validação em
hardware quântico (IBM `ibm_fez`, fidelidade 0.997). Narrativa honesta aplicada no
README, MATH.md e ARCHITECTURE.md: quântico é origem da pesquisa, não dependência
de produção.

## Testes
`cargo test` — **11/11** · `cargo stylus check` — aprovado (22,5 KiB) ·
`engine/demo.py` — **40/40, <0,1 ms/tx** · `engine/honesty_experiment.py` — **0 divergências**.
