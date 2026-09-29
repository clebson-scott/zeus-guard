# ZEUS GUARD — Oráculo Analítico (v5)

O score de risco agora carrega **prova criptográfica**: só vale on-chain se for assinado
pelo oráculo oficial. Atacante que forjar um score "liberado" é rejeitado no `ecrecover`.

```
extensão MV3 ──POST /score──▶ oracle_service.py ──assinatura──▶ extensão
                                                                   │
dApp/agent ──check_tx_signed(user, amount, risk, nonce, sig)──▶ contrato Stylus
                                                                   │
                                        precompile 0x01 (ecrecover) ─┘
                                        signer == trusted_oracle ?
```

## Barreiras de `check_tx_signed` (lib.rs)

1. **Reentrância** (`reentrancy_locked`)
2. **Disjuntor**: sessão congelada → aborta
3. **Hash reconstruído nos bytes exatos** (sem padding do address)
4. **ecrecover via precompile 0x01** + `signer == trusted_oracle`
5. **Anti-replay**: `keccak(user‖nonce)` já usado → rejeita
6. **Política v4** (`policy_gate`): sessão existe, risco < 6000 (60%), teto diário

> Nota técnica: `stylus-sdk 0.10` não exporta `crypto::ecrecover` — a recuperação usa o
> precompile EVM nativo (`RawCall::new_static`), mockável nos testes unitários.

## Alinhamento de bytes (o pulo do gato)

```
hash = keccak256( user(20B, SEM padding) || amount(32 BE) || risk(32 BE) || nonce(32 BE) )
```

O servidor Python replica essa concatenação **crua**. Codificações `eth_abi` fazem padding
do address para 32 bytes e **não batem** com o contrato. O vetor de teste é travado dos dois
lados (`oraculo_hash_bate_com_o_servidor_python` no Rust e `[1]` no `test_oracle_service.py`).

## Operação

```bash
# 1. gere o par de chaves do oráculo (uma vez)
python3 generate_keys.py
#    → Endereço público: init_oracle() no contrato
#    → Chave privada: ORACLE_PRIVATE_KEY no .env (NUNCA comite — já está no .gitignore)

# 2. teste o alinhamento
python3 engine/test_oracle_service.py

# 3. suba o servidor (porta 8080, sem debug)
python3 engine/oracle_service.py

# 4. inicialize o contrato com o endereço público
#    check_tx_signed(user, amount, risk, nonce, assinatura)
```

A extensão consulta `ORACLE_ENDPOINT` (`ext/zeus_hook.js`) antes de abrir a carteira;
se o oráculo cair, o firewall local on-chain (registro de revogação) continua valendo
(modo de contingência) — o bloqueio do oráculo, porém, nunca vira falha silenciosa.
