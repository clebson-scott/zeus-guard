# ZEUS GUARD — Oráculo Analítico (v6 — Enforcement Absoluto / Nota 10)

O score de risco carrega **prova criptográfica multisig**, e desde a v6 o oráculo está
**NO CAMINHO DO DINHEIRO**: `vault_send` só move fundos com um bundle de assinaturas
válido (threshold 2-de-3). Sem assinatura, sem transferência — sem bypass.

```
extensão MV3 ──POST /score──▶ oracle_service.py ──bundle 2-de-3──▶ extensão
                                        │
                        features REAIS via RPC (extract_features)
                        argmin determinístico (honesty_experiment)
                                        │
dApp/agente ──vault_send(user, token, payee, amount, risk, nonce, sigs[])──▶ contrato Stylus
                                                                                   │
                                              multisig: ecrecover por sig, 2 slots distintos
                                              domain separation: chain_id + address(this)
                                              anti-replay: nonce consumido uma única vez
```

## Os 5 pontos do design v6

| # | Déficit v5 | Solução v6 |
|---|-----------|------------|
| 1 | Oráculo consultivo (bypass em `vault_send`) | **Enforcement**: `vault_send` exige `nonce` + `signatures[]`; verifica internamente e reverte se o threshold não for atingido |
| 2 | Replay cross-chain/cross-deploy | **Domain separation**: `keccak256(abi.encode([user, token, payee, chain_id, contract, amount, risk, nonce]))` — 256 bytes espelhados nos dois lados |
| 3 | Chave one-shot (vazou = redeploy) | **Rotação**: papel `contract_owner` + `update_oracle_key(antiga, nova)` |
| 4 | Motor stub (base_score fixo) | **Motor real**: `extract_features` lê o estado REAL via RPC; `argmin_classify` do `honesty_experiment.py` decide; Gibbs do QCSN atesta (fail-closed se divergir) |
| 5 | Oráculo único (ponto central de confiança) | **Multisig 2-de-3**: 3 slots de oráculos, threshold mínimo de 2 assinaturas distintas |

## Barreiras de `vault_send` v6

1. **Reentrância** (`reentrancy_locked`)
2. **Autorização v4** (sessão, owner/guardian, token configurado)
3. **Conjunto de oráculos inicializado** + **sessão congelada** (disjuntor)
4. **Hash com domain separation** — reconstruído nos mesmos 256 bytes assinados
5. **ecrecover por assinatura** (precompile EVM 0x01) + contagem **distinct** por slot
6. **Threshold 2** + parse estrito (65 bytes, v normalizado, **s-malleability rejeitada**)
7. **Anti-replay**: `keccak(user‖nonce)` consumido exatamente uma vez
8. **Política v4** (`policy_gate`): risco < 6000, teto diário

> `preflight_signed` é a leitura sem efeito colateral (não consome nonce) para o dApp
> checar antes de submeter o `vault_send` com o **mesmo** nonce.

## Alinhamento de bytes (o contrato da proteção)

```
hash = keccak256( eth_abi.encode(['address','uint256','uint256','uint256','uint256','address'],
                                 [user, chain_id, amount, risk_x100, nonce, contract]) )
```

O Rust concatena `pad32(user) ‖ chain_id ‖ amount ‖ risk ‖ nonce ‖ pad32(contract)` —
byte-a-byte idêntico ao `eth_abi.encode` (provado nos vetores travados em
`oraculo_hash_v6_bate_com_o_servidor_python` e `tests::[1]` do `test_oracle_service.py`).

## Operação

```bash
# 1. gere o CONJUNTO multisig (uma vez) — 3 chaves, threshold on-chain = 2
python3 generate_keys.py
#    → init_oracle([o1, o2, o3]) no contrato com os endereços públicos
#    → ORACLE_PRIVATE_KEY_1/2/3 no .env (NUNCA comite — já está no .gitignore)

# 2. suítes de alinhamento e segurança
cd zeus-guard-contract && cargo test        # Rust: 19/19
python3 engine/test_oracle_service.py       # Python: 16/16

# 3. suba o servidor (porta 8080, sem debug)
python3 engine/oracle_service.py            # /score e /health

# 4. .env do servidor
#    ORACLE_PRIVATE_KEY_1=...  ORACLE_PRIVATE_KEY_2=...  (3 opcional)
#    ZEUS_RPC=https://sepolia-rollup.arbitrum.io/rpc
#    ZEUS_CHAIN_ID=421614
#    ZEUS_CONTRACT_ADDRESS=0x...   # endereço do deploy v6
```

A extensão consulta o oráculo antes de abrir a carteira; se o oráculo cair, o modo de
contingência mantém o firewall on-chain local — mas o cofre v6 só move dinheiro com o
bundle multisig: indisponibilidade do oráculo **nunca** vira transação liberada.
