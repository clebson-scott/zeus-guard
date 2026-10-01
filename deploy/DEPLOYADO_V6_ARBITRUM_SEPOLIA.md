# Deploy v6 Hardened — Enforceamento Absoluto (Canônico)

**Data:** 01/10/2026 17:46 UTC
**Contrato v6 (hardening-v6, PR #1, merge 316f7d8):** `0x9b7608536a9704e120f0fc2c6722e2abb0fef848`
**Rede:** Arbitrum Sepolia (chain_id 421614) — Stylus
**Explorer:** https://sepolia.arbiscan.io/address/0x9b7608536a9704e120f0fc2c6722e2abb0fef848
**Status:** ativo, ativado e **cacheado no ArbOS** (bid tx `0x7b78367c0660e935d2f6d65a939b02d54e8107e15bf5d3b3ed57390fcf9e2fc9`) — chamadas mais baratas.

## Transações do deploy

| Etapa | Hash |
|---|---|
| Deploy (create program) | `0x5949e1a6171150a083462229b87886c8f28a4b0e3fe8a115d98ca9ad127deb87` |
| Ativação (wasm data fee 0.000193 ETH) | `0xe03bf002902d8e2ca9e731a879582029c1ecd76d074c13809b3b568235d7789b` |
| initOracle (multisig 2-de-3) | `0x089e87d708a9d6145923ed18e901be457f6d7108c6228bd0679b7be6699a935b` (bloco 314711915, status 1) |
| Cache bid ArbOS (bid 0) | `0x7b78367c0660e935d2f6d65a939b02d54e8107e15bf5d3b3ed57390fcf9e2fc9` |

Conjunto multisig registrado nesta build (verificável via `oraclesPub()`):

| Oraculo | Endereco publico |
|---|---|
| 1 | `0xb1cc9aF848BC1622B064022977419a5e1A86193B` |
| 2 | `0xd24a476D8da9a15D20c919028ef9B3e285a07BA1` |
| 3 | `0xa34EED87Db0570f5A26E719C844e92e2Bb402Db6` |

Threshold on-chain: **2** (`oracleThresholdPub()`), WASM: 32,0 KB (31.977 bytes).

## Prova red-team AO VIVO (01/10/2026): 10 PASS / 0 FAIL

`python3 proof/test_integration_v4.py` com `ZEUS_GUARD_CONTRACT_ADDRESS=0x9b7608536a9704e120f0fc2c6722e2abb0fef848`:

```
[ATAQUE 1] Forged-Risk (risk=0 injetado, 2 assinaturas do invasor)
           -> OracleThresholdNotMet {got: 0, needed: 2}   PASS
[ATAQUE 2] Bundle-swap (bundle assinado sobre risk=9500, calldata com risk=0)
           -> OracleThresholdNotMet {got: 0, needed: 2}   PASS
[ATAQUE 3] Replay real on-chain (gas pago, hash publico):
           1a submissao do bundle legitimo  -> status=1   PASS (nonce consumido)
           replay do MESMO nonce            -> status=0   PASS (anti-replay morto)
```

Alem disso: hash v6 == vetor canônico do Rust (`0569bd23…`) e domain separation
(outra chain / outro deploy / outro token / outro payee => outro hash) — 5 PASS.
Tudo verificado com eth_call/txs reais contra este endereco.

## O que esta versao trava

- **Enforcement absoluto:** `vault_send` exige nonce + bundle de assinaturas do
  oraculo (multisig 2-de-3) — o oraculo esta NO CAMINHO DO DINHEIRO.
- **Domain separation:** hash assinado inclui chain_id + address(this)
  (espelho eth_abi de 256 bytes — replay cross-chain/cross-deploy morto).
- **Rotacao de chave:** `updateOracleKey(antiga, nova)` pelo `contract_owner`.
- **ABI bytes[]:** `Vec<Bytes>` exporta `bytes[]` nativo (casa com eth_abi).

## Observacoes de deploy (reproducao)

- O RPC oficial `sepolia-rollup.arbitrum.io` recusou a simulacao de ativacao
  (-32000 "stylus activations not allowed for this request"). O deploy desta build
  foi feito via `https://arbitrum-sepolia-rpc.publicnode.com` (chain_id `0x66eee`).
- Comandos completos: `zeus-guard-contract/deploy.sh` (mesmo fluxo; ajuste ZEUS_RPC
  se o RPC oficial continuar bloqueando ativacoes).
- A carteira deployer e testnet-only (`DEPLOY_KEY_NAO_USAR_EM_MAINNET.txt`, fora do repo).

## Historico de contratos

| Versao | Endereco | Estado |
|---|---|---|
| v2 | `0x038409e301e32467b226d10c728a0c6fbe28ea4a` | historico |
| v3 | `0xe22d42…` (ver DEPLOYADO_V3) | historico |
| v4 | `0xa9ef4e9be0e8f45e737f361380743faab72fe76a` | vivo — contrato da demo web |
| v6 (pre-hardening) | `0x4a7cdfa8ca7a3969b3427c42948abbd988097dd9` | obsoleto (dominio/ABI antigos) |
| **v6 hardened (esta build)** | `0x9b7608536a9704e120f0fc2c6722e2abb0fef848` | **canônico** |
