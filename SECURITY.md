# 🔐 SECURITY.md — ZEUS GUARD: Postura de Segurança, Modelo de Ameaças e Pacote de Auditoria

## Estado Atual da Release (27/09/2026 — Release Candidate v4)

**Testnet Ativa (Arbitrum Sepolia, Chain ID 421614). Auditado e Corrigido Internamente.**
Este documento compõe o pacote pronto para auditoria externa (*audit-ready*). Todo o código-fonte, modelo de ameaças, superfícies de ataque, invariantes formais e testes foram validados e congelados nesta versão.

- **Contrato Canônico Deployado (v4):** [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a)
- **Status Mainnet:** **ESTRITAMENTE BLOQUEADO**. Nenhum deploy em Mainnet é realizado sem (1) auditoria externa formal por firma especializada e (2) configuração de chave/multisig de produção.

---

## Superfície de Ataque e Mitigações Verificadas (Auditoria Interna v4)

| Área / Vetor | Risco Identificado | Mitigação Implementada no Código | Estado de Validação |
|---|---|---|---|
| **Autorização de Cofre (`vault_send`)** | Terceiro não autorizado tentar mover fundos do cofre | `is_vault_authorized(sender, owner, guardian)` verifica rigorosamente o papel do invocador. Terceiros revertem com `NotVaultAuthorized`. | **Passou em Testes Nativo e On-Chain** |
| **Restrição Estrita de Token** | Ataque de substituição de token ERC-20 na custódia | `is_token_allowed(configured, token)` valida contra o token USDG da sessão (`session_usdg`). Tokens não permitidos revertem imediatamente. | **Passou em Testes Nativo e On-Chain** |
| **Reentrância Financeira** | Reentrância em chamadas externas ERC-20 (`RawCall`) | Trava explícita de reentrância (`ReentrancyGuard`) em `escrow_payment`, `release_payment`, `refund_disputed` e `vault_send`. | **Passou em Testes Nativo** |
| **Bypass de Configuração de Sessão** | Alterar políticas com sessão congelada | `init_session`, `log_approval`, `set_usdg_token` e `update_policy` validam `session_frozen` e revertem com `SessionFrozenError`. | **Passou em Testes Nativo** |
| **Contabilidade de Teto Diário & Reembolso** | Inconsistência de limite diário em janelas rolantes e refunds | `restore_daily_spent` avalia a janela de 24h corrente via `current_daily_spent` antes de recalcular o saldo do cap diário. | **Passou em Testes Nativo e On-Chain** |
| **Inputs Extremos / Panics de Conversão** | Exploits de integer overflow com `U256` | Tratamento seguro via `amount_fits_u128`, `risk_saturating` e `u64_saturating`. Entradas fora de limite revertem com `AmountTooLarge` tipado. | **Passou em Testes Nativo e On-Chain** |
| **Assinaturas Off-Chain & Permits EIP-712** | Phishing via permit sem checagem de revogação | Extensão MV3 injeta `zeus_hook.js` em `document_start` e consulta `approval_status_pub` no contrato v4 antes da tela da carteira. | **Passou em Testes Node.js 7/7** |
| **Falha ou Indisponibilidade do Guardião** | Bloqueio total da carteira do usuário | Suporte declarativo aos modos `FAIL_OPEN` (fallback seguro com aviso ao usuário) e `FAIL_CLOSED` (opção estrita que bloqueia com código 4001). | **Passou em Testes Node.js 7/7** |

---

## Invariantes Formais do Smart Contract

1. **Custódia Segura de Valor:** Nenhum valor sai do cofre sem assinatura válida de `owner`, `payee` autorizada, ou reembolso fundamentado do `guardian`.
2. **Separação de Papéis no Cofre:** `vault_send` exige `is_vault_authorized` e `is_token_allowed`.
3. **Imutabilidade Sob Congelamento:** Quando `session_frozen == true`, mutações no contrato revertem com `SessionFrozenError`.
4. **Respeito Estrito à Deadline de Disputa:** Pagamentos sob disputa de 3 dias (`dispute_deadline_of`) não podem ser liberados ao payee (`PaymentDisputed`), nem reembolsados duas vezes (`AlreadyRefunded`).
5. **Ausência de Panic em Tipos Numéricos:** Inputs excedendo 128 bits devolvem erro tipado `AmountTooLarge`.
6. **Proteção Reentrante Ativa:** Nenhuma transferência externa de token permite reentrância nos métodos financeiros.

---

## Modelo de Confiança Declarado

- **Contratos vs Assinaturas EOA:** A blockchain EVM não permite revogação retroativa de um `approve` por terceiros sem a chave do dono. A arquitetura ZEUS combina (a) **leitura prévia de revogação pública** (`approval_status_pub`) na camada de carteira/extensão antes de assinar, e (b) **custódia em cofre USDG** com janela de desafio para liquidações agênticas.
- **Limites do Guardião:** O guardião possui privilégios estritamente defensivos (bloqueio e reembolso de disputas). Ele não pode alterar o limite diário nem sacar fundos para endereços arbitrários sem autorização da sessão.
- **Indisponibilidade:** Em falha do guardião, a extensão opera por padrão em `FAIL_OPEN` (avisando o usuário), configurável para `FAIL_CLOSED`.

---

## Suíte de Testes e Ferramentas Executadas

Todos os comandos foram executados de forma determinística e reproduzível:

```bash
# 1. Testes Nativos do Contrato Stylus (15/15 passando)
cd zeus-guard-contract && cargo test

# 2. Verificação de WASM e ABI Stylus (23,4 KiB)
cd zeus-guard-contract && cargo stylus check

# 3. Teste de Equivalência do Motor QCSN (quench vs argmin: 0 divergências em 1.863 casos)
python3 engine/honesty_experiment.py

# 4. Benchmark em Dados Reais da Arbitrum Mainnet (100% recall, 11,9% FP, acurácia 90,1%)
python3 engine/realdata_benchmark.py

# 5. Suíte de QA da Extensão MV3 e Hook EIP-1193 (7/7 passando)
node ext/test_extension.js

# 6. Smoke Tests On-Chain v4 na Arbitrum Sepolia (13/13 passando)
python3 proof/smoke_v4.py

# 7. Simulação de Ataque & Defesa Vivo (4/4 passando)
python3 proof/live_attack_defense.py --rpc https://sepolia-rollup.arbitrum.io/rpc --contract 0xa9ef4e9be0e8f45e737f361380743faab72fe76a --victim 0x1718bd9000B81bD5996DeE981eb76232bc2438B3
```

---

## Checklist de Auditoria

O checklist detalhado para auditores externos encontra-se em [`docs/AUDIT_CHECKLIST.md`](AUDIT_CHECKLIST.md).
