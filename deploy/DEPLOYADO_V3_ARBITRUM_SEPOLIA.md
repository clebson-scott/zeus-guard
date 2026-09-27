# ⚡ ZEUS GUARD v3 — DEPLOY OFICIAL NA ARBITRUM SEPOLIA

**Data:** 26/09/2026, ~01h15 UTC
**Rede:** Arbitrum Sepolia (chainId 421614)
**Contrato v3:** `0xe22d42fce3651e4a0ddb279f83dc84d120cfa35f`
**Explorer:** https://sepolia.arbiscan.io/address/0xe22d42fce3651e4a0ddb279f83dc84d120cfa35f
**Carteira deploy:** `0x1718bd9000B81bD5996DeE981eb76232bc2438B3` (testnet-only)
**Commit:** `c7bcb1f` (v3: audit fixes — risk enforced in escrow path, typed AmountTooLarge, dispute deadline)

## Transações
| Etapa | Hash |
|---|---|
| Deploy (initcode) | `0xcff3dff100cbd90ad3feb4e451d230fac8a8f0a3e972ee4b213285604ba2ee53` |
| Ativação Stylus | `0xd5158d2119856f277891ab9cf0d5bdd4d4f1cb1bf36cbfe1c2a36d3d9de8ffd1` |

**Metadados:** wasm 22,0 KiB (22.501 bytes), data fee 0,000139 ETH,
metadata hash `9f5bda81e3eda1103387256fcd441ea8253eedce6fef348dbfec6233f746ae3c`,
toolchain stylus 0.6.3, stylus-sdk 0.10.9, `cargo stylus deploy --no-verify`.

## Pipeline de financiamento (100% grátis, Lei 4)
1. **Faucet PoW** (sepolia-faucet.pk910.de): claim `0xa71af249e19952040d867b6e40fe0aa441cddebf40dd5224562a0cb78b300459` → **0,06575 SepETH**
   (sessão capturada via DevTools, claim pela API direta `POST /api/claimReward`)
2. **Ponte oficial Sepolia → Arbitrum Sepolia**: `depositEth()` no Delayed Inbox
   `0xaAe29B0366299461418F5324a79Afc425BE5ae21`
   TX L1: `0xf5786c021393f9bf6e2299401e1afe5691fbb4d3f29b420ccdb8a0fedeb6d735` (bloco 11789913, gas 91.174) → 0,06556 ETH na L2

## Teste de fumaça on-chain (16/16 comportamentos corretos)
Fixes da auditoria verificados AO VIVO com transações reais:

### v3 Fix #1 — risco >= 60% bloqueia o caminho do DINHEIRO
- `escrowPayment` com risk=9000 (90%): ⛔ `TooRisky` — o firewall agora vale no escrow
- `escrowPayment` com risk=10 (1%): ✅ escrowado on-chain (tx `0xa9a1c5870ee7c1…`)
- `escrowPayment` id duplicado: ⛔ `PaymentIdInUse`

### v3 Fix #2 — erro tipado em vez de panic (valores > 2^128)
- `escrowPayment` com 2^130 wei: ⛔ `AmountTooLarge` (erro tipado, sem panic)

### v3 Fix #3 — disputa com prazo e release protegido
- `disputePayment` on-chain: ✅ (tx `0x74bf693bf3b8c5…`)
- `releasePayment` durante disputa: ⛔ `PaymentDisputed`
- `refundDisputed`: ✅ on-chain (tx `0xf298fa1795ba2f…`)

### Firewall de leitura (política única)
- `checkTx` risk=9000: ⛔ `TooRisky`
- `checkTx` risk=5999 (limiar - 1): ✅ passa
- `checkTx` acima do teto: ⛔ `AboveDailyCap`
- `checkTx` congelado: ⛔ `SessionFrozenError`

### Ciclo de emergência
- `emergencyFreeze`: ✅ tx `0x45f0664d1f5250…` → `sessionFrozenPub == true`
- `unfreeze`: ✅ tx `0xa9ee7a14bb0a4d…` → `sessionFrozenPub == false`
- `guardianRevoke`: ✅ tx `0x2d6501777e3053…`

## Testes nativos
`cargo test` — **11/11 passando** (v3 adicionou testes dos fixes da auditoria).
`cargo stylus check` — wasm aprovado, sem violações.
