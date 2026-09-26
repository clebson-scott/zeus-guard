# ⚡ ZEUS GUARD v2 — DEPLOY OFICIAL NA ARBITRUM SEPOLIA

**Data:** 26/09/2026, ~01h45 UTC
**Rede:** Arbitrum Sepolia (chainId 421614)
**Contrato v2:** `0x038409e301e32467b226d10c728a0c6fbe28ea4a`
**Explorer:** https://sepolia.arbiscan.io/address/0x038409e301e32467b226d10c728a0c6fbe28ea4a
**Carteira deploy:** `0xf92721394140c43C72FbfF2f0ebf90327fD2bF9D` (testnet-only)

## Novidades v2
- Cofre USDG **nativo**: `setUsdgToken(token)` liga o modo real — `escrowPayment` puxa USDG via `IERC20.transferFrom`; `address(0)` mantém o modo ledger (compatível com receipts v1).
- `refundDisputed`: guardião devolve pagamento contestado ao pagador.
- Testes nativos de unidade (3/3): `cargo test`.
- Contrato: 21,9 KB WASM, data fee 0,000135 ETH.

## Transações v2
| Etapa | Hash |
|---|---|
| Deploy (initcode) | `0x0227ef40a5b9d199e3eff80c9630879fdf90b2798beb32665fa3338b4d06e672` |
| Ativação Stylus | `0x2e658e8abb37549d42671da8970bc3b06f053c2c83bc2d03ed72c00033f51978` |
| Cache bid ArbOS | `0xa6f19477c67b6209b167c183a21bd9e141dd47023d4acccb2e6b01e76f5797e2` |
| Sessão demo (initSession, gas 155.531) | `0x8cc71c04e82ca8d0247a541d6669b2a3c44be8377b64ec01229293301c854ead` |

## Smoke test v2 (26/09/2026, atestado vivo — ABI camelCase)
- `checkTx` risco 150, 50 USDG: ✅ LIBERADA (retorno vazio = sucesso)
- `checkTx` risco 9500 (drainer QCSN): ⛔ `TooRisky` (0xcc65e730, risco 9500 ≥ 6000)
- `checkTx` 600 USDG com teto 500: ⛔ `AboveDailyCap` (0x73fede4c, pedido 600 / restante 500)
- `checkTx` sem sessão: ⛔ `NoSession` (0xaabbee68)
- `releasePayment` logo após `escrowPayment`: ⛔ `ChallengeWindowOpen` (0x4bc3cfba) — janela de desafio blindada, comportamento correto
- `sessionExists` / `sessionWindowPub` / `sessionCapPub`: true / 3600s / 500 USDG ✓

## Nota técnica honesta (Lei 4)
O SDK Stylus exporta os nomes de função em **camelCase** (`sessionExists`, não
`session_exists`). Um dia de diagnóstico começou com "contrato quebrado" e terminou em
"chamada com seletor errado reverte com dado vazio". Documentado no
JUDGE_VERIFICATION.md para o juiz não perder 10 minutos no mesmo poço.
