# Deploy v6 — Enforceamento Absoluto (Nota 10)

**Data:** 29/09/2026 05:16 UTC
**Contrato v6:** `0x4a7cdfa8ca7a3969b3427c42948abbd988097dd9`
**Rede:** Arbitrum Sepolia (chain_id 421614) — Stylus
**Explorer:** https://sepolia.arbiscan.io/address/0x4a7cdfa8ca7a3969b3427c42948abbd988097dd9

## O que esta versao trava

- **Enforcement absoluto:** `vault_send` exige nonce + bundle de assinaturas do
  oraculo (multisig 2-de-3) — o oraculo esta NO CAMINHO DO DINHEIRO.
- **Domain separation:** hash assinado inclui chain_id + address(this)
  (espelho eth_abi de 192 bytes — replay cross-chain/cross-deploy morto).
- **Rotacao de chave:** `updateOracleKey(antiga, nova)` pelo `contract_owner`.
- **Motor real:** score via /score do oraculo (features reais RPC + argmin).

## Conjunto multisig registrado (initOracle)

| Oraculo | Endereco publico |
|---------|------------------|
| 1 | `0xc5c406d425ABBAb22d80484843Ed20467e44653a` |
| 2 | `0xAdB9d1Ad57a6eB70E6830e49a2460eE7f76ADA1C` |
| 3 | `0xb10D19DB5bA6A7829A31AAD45D702eDA8B03004d` |

Threshold on-chain: **2** (`oracleThresholdPub()`).

## Correcao critica desta build (bytes[] no ABI)

O stylus-sdk exporta `Vec<Vec<u8>>` como `uint8[][]` — seletores de clientes
que usavam `bytes[]` nao batiam (revert seco sem erro tipado). A troca para
`Vec<Bytes>` no lib.rs exporta `bytes[]` nativo e casa com Solidity/eth_abi.

## Prova red-team AO VIVO (29/09/2026): 8 PASS / 0 FAIL

```
[ATAQUE 1] Forged-Risk  -> OracleThresholdNotMet {got: 0, needed: 2}
[ATAQUE 2] Bundle-swap  -> OracleThresholdNotMet {got: 0, needed: 2}
[ATAQUE 3] Bundle legitimo confirmado (status=1); replay do MESMO nonce
           revertido on-chain (status=0) — anti-replay real
```

Reproducao:

```bash
export ZEUS_GUARD_CONTRACT_ADDRESS=0x4a7cdfa8ca7a3969b3427c42948abbd988097dd9
export ATTACKER_PRIVATE_KEY=0x...        # carteira de testnet com gas
export ZEUS_ORACLE_BUNDLE_FILE=...       # bundle LIBERAR do /score
python3 proof/test_integration_v4.py     # 8 pass / 0 fail
```

No `.env` do `engine/oracle_service.py` (chaves privadas NUNCA no repo):

```
ZEUS_GUARD_CONTRACT_ADDRESS=0x4a7cdfa8ca7a3969b3427c42948abbd988097dd9
ORACLE_PRIVATE_KEY_1=0x...
ORACLE_PRIVATE_KEY_2=0x...
ORACLE_PRIVATE_KEY_3=0x...
```
