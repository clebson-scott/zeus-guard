# ⚡ ZEUS GUARD — DEPLOY OFICIAL NA ARBITRUM SEPOLIA

**Data:** 23/09/2026, 17h06 UTC
**Rede:** Arbitrum Sepolia (chainId 421614)
**Contrato:** `0x313e9994f1e77f579e797c19e29250a9a782e3a5`
**Explorer:** https://sepolia.arbiscan.io/address/0x313e9994f1e77f579e797c19e29250a9a782e3a5
**Carteira deploy:** `0xf92721394140c43C72FbfF2f0ebf90327fD2bF9D` (chave testnet-only, em deploy/DEPLOY_KEY_NAO_USAR_EM_MAINNET.txt)

## Transações
| Etapa | Hash |
|---|---|
| Deploy (initcode) | `0xc893dbc4c59a1fd11abf054f1c4c81a6054b4da187df700a3f41e6a41c1fcfcb` |
| Ativação Stylus | `0x1e3515c1d6d9565fc12e0f4c2ae311ee77868131b23666a06de7d9f01773fe59` |
| initSession (demo) | `0xdae3b9202632fead32...` (gas 177.562) |

## Pipeline de financiamento (100% grátis, Lei 4)
1. **Faucet PoW** (sepolia-faucet.pk910.de): mineração honesta 46,6 H/s → **0,064 SepETH**
   (sessão ed664b4d, claim em 40 min, custo R$ 0)
2. **Ponte oficial Sepolia → Arbitrum Sepolia**: `depositEth()` no Delayed Inbox
   `0xaAe29B0366299461418F5324a79Afc425BE5ae21`
   TX L1: `0x805327fb592e2a167d0285c288390a6212d46fb6ff0f4fc01d0e5e6b083dde1c` → 0,06 ETH na L2
3. **Deploy:** `cargo stylus deploy --no-verify` (toolchain 1.98.1, stylus-sdk 0.10.9,
   wasm data fee 0,000124 ETH, contrato 19,2 KB)

## Teste de fumaça on-chain (atestado vivo)
- `checkTx` risco 250: ✅ LIBERADA
- `checkTx` risco 6000 (drainer QCSN, limiar RISK_BLOCK_X100=6000): ⛔ `TooRisky` (0xcc65e730)
- `checkTx` 0,6 ETH com teto 0,5: ⛔ `AboveDailyCap` (0x73fede4c)
- `checkTx` sem sessão: ⛔ `NoSession` (0xaabbee68)

## Estado das carteiras após tudo
- L1 Sepolia: ~0,004 SepETH
- L2 Arbitrum Sepolia: ~0,0597 ETH (sobra p/ demos e cache bid)

## Cache ArbOS (26/09/2026, nota 10)
- `cargo stylus cache bid 0x313e9994f1e77f579e797c19e29250a9a782e3a5 0`
- TX: `0xe51c05312b723a818aa3d3c08009f0e8210be856a66510820ae8bf459dbdace6`
- Contrato agora fica em cache nativo do ArbOS: ativação garantida e barata para qualquer usuário.

## Próximos passos p/ submissão HackQuest
- [x] `cargo stylus cache bid` executado em 26/09/2026 (TX `0xe51c...ace6`)
- [ ] Vídeo demo (voz clonada Clebson) apontando pro endereço acima
- [ ] README com link do explorer + submissão até 04/10 15h59 UTC

> **Sucessor:** a v2 (cofre USDG real + reembolso) está em
> [`DEPLOYADO_V2_ARBITRUM_SEPOLIA.md`](DEPLOYADO_V2_ARBITRUM_SEPOLIA.md) —
> contrato `0x038409e301e32467b226d10c728a0c6fbe28ea4a`. Este documento registra a v1 original.
