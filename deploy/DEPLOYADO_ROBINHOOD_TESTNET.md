# ZEUS GUARD v6 — DEPLOYADO NA ROBINHOOD CHAIN TESTNET (chain 46630)

**Data:** 02/10/2026
**Autor:** Clebson Campos de Araujo (solo builder — Arbitrum Open House Singapore 2026)

## Resumo
O contrato ZEUS GUARD v6 hardened (mesmo código do deploy canônico da
Arbitrum Sepolia, `0x9b7608536a9704e120f0fc2c6722e2abb0fef848`) foi deployado e
**ativado na Robinhood Chain Testnet** — a rede do slot de prêmio reservado do
Arbitrum Open House Singapore (mínimo 1 dos 3 prêmios reservado a projetos na
Robinhood Chain; US$ 1 mi comprometidos pela Robinhood para atividade de devs
na testnet).

## Endereços e transações

| Item | Valor |
|---|---|
| **Contrato v6 (Robinhood Chain Testnet)** | `0xe18332679dc0bcfd1dda9e2e022252cbadb65eb5` |
| Deployment tx | `0x9e833ccdfc3555f18a8e3331aa86007e139223cbe1d832be5f38f6a6c8cb608d` |
| Ativação Stylus (ArbWasm) | `0xc479573ff3469064ff313081aca9dddd27a57a58817c174639f118d0f388459e` |
| init_oracle (multisig 2-de-3) | `0x37a7d18d011dc338738dc796b17cbfd9e24f2989c4ab32c1a04cb0ba5a330ce3` |
| WASM data fee | 0,000193 ETH (com bump de 20%) |
| Explorer | https://explorer.testnet.chain.robinhood.com/address/0xe18332679dc0bcfd1dda9e2e022252cbadb65eb5 |

Conjunto multisig do oráculo registrado on-chain (igual ao da Arbitrum Sepolia,
verificável via `oraclesPub()`):

| Oráculo | Endereço público |
|---|---|
| 1 | `0xb1cc9aF848BC1622B064022977419a5e1A86193B` |
| 2 | `0xd24a476D8da9a15D20c919028ef9B3e285a07BA1` |
| 3 | `0xa34EED87Db0570f5A26E719C844e92e2Bb402Db6` |

Threshold on-chain: **2** (`oracleThresholdPub()`).

## Smoke test on-chain (executado ao vivo, 02/10/2026)

| Cenário | Resultado |
|---|---|
| `checkTx` sem sessão | reverte `NoSession` ✓ |
| `initSession` (janela 3600s, teto 0,01 ETH) | status 1 ✓ |
| `sessionExists` | `true` ✓ |
| `checkTx` 0,001 ETH, risco 0 | **Ok** (sem revert) ✓ |
| `checkTx` risco 6500 | reverte `TooRisky(6500 ≥ 6000)` ✓ |
| `checkTx` 0,05 ETH (teto 0,01) | reverte `AboveDailyCap(requested, remaining=0.01 ETH)` ✓ |
| `oraclesPub()` / `oracleThresholdPub()` | 3 oráculos / threshold 2 ✓ |

## Pipeline de financiamento (100% dentro das regras, sem faucet social)
Não há faucet público sem login social para esta testnet (o oficial exige
Cloudflare + Google Sign-In; o QuickNode exige saldo mainnet; o Thirdweb exige
conectar carteira). Rota usada: **ponte canônica Arbitrum** a partir de saldo
residual de testnet:

1. Carteira deployer `0xf92721394140c43C72FbfF2f0ebf90327fD2bF9D` com saldo
   residual na Ethereum Sepolia (L1, pai da Robinhood Chain Testnet).
2. `depositEth()` no Delayed Inbox da testnet deles
   (`0xF2939afA86F6f933A3CE17fCAB007907B6b0B7a4`, L1 Sepolia):
   tx `0x48db6ea47a529b36717b28955f5c4dce6f6fb1f42311c3d2f204cd34e998e6ff`
   (bloco 11825539, 0,0034 ETH, evento MessageDelivered pelo Bridge
   `0x96295BDad104eaD97cC08797b3dC68efF59CcF30`).
3. ETH entregue na L2 via delayed inbox (Orbit delay ~15 min) → deploy + ativação.

## Detalhes da rede
- Chain ID: `46630`
- RPC usado: `https://robinhood-sepolia-rpc.publicnode.com`
  (o RPC oficial `rpc.testnet.chain.robinhood.com` bloqueia trials de ativação
  Stylus — mesmo comportamento já documentado com o RPC oficial da Arbitrum
  Sepolia)
- Stylus (ArbWasm precompile `0x71`) suportado; cache bid de contrato
  **indisponível nesta chain** (ArbWasmCache sem cache managers —
  "Stylus cache not yet enabled on this chain", resposta do próprio comando
  `cargo stylus cache bid`). Chamadas funcionam normalmente sem cache.
- USDG canônico na Robinhood Chain mainnet: `0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168`
  (na testnet não há código nesse endereço ainda — a integração USDG do cofre
  é nativa por design, pronta para a mainnet).

## Como reproduzir

```bash
# 1. ponte canônica (L1 Sepolia -> Robinhood Chain Testnet)
cast send 0xF2939afA86F6f933A3CE17fCAB007907B6b0B7a4 \
  "depositEth()" --value 0.0034ether \
  --rpc-url https://ethereum-sepolia-rpc.publicnode.com --private-key $KEY

# 2. deploy + ativação
cargo stylus deploy --no-verify --max-fee-per-gas-gwei 0.1 \
  --endpoint https://robinhood-sepolia-rpc.publicnode.com --private-key $KEY

# 3. oráculo multisig
cast send 0xe18332679dc0bcfd1dda9e2e022252cbadb65eb5 \
  "initOracle(address[])" "[0xb1cc...,0xd24a...,0xa34E...]" \
  --rpc-url https://robinhood-sepolia-rpc.publicnode.com --private-key $KEY

# 4. smoke test (mesma sequência da tabela acima)
cast call 0xe18332679dc0bcfd1dda9e2e022252cbadb65eb5 \
  "checkTx(address,uint256,uint256)" $USER 1000000000000000 6500 \
  --rpc-url https://robinhood-sepolia-rpc.publicnode.com   # TooRisky(6500, 6000)
```
