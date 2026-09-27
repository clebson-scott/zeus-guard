# 📋 Checklist de Auditoria Externa — ZEUS GUARD (v4 Release Candidate)

Este checklist orienta auditores externos na revisão formal do pacote **ZEUS GUARD v4**. Cada item possui comandos de verificação reproduzíveis e localização no código-fonte.

---

## 1. Smart Contract (Stylus / Rust v4)

- [ ] **Autorização de Cofre e Sacada (`vault_send`)**
  - **Invariante:** Apenas o `owner` ou o `guardian` autorizado pode executar saques do cofre.
  - **Verificação:** `is_vault_authorized(sender, owner, guardian)`. Chamadas por terceiros revertem com `NotVaultAuthorized`.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Teste:** `tests::vault_send_autorizacao_e_restricao_de_token`

- [ ] **Restrição de Token Permito no Cofre (`session_usdg`)**
  - **Invariante:** Transferências e custódia em `escrow_payment` e `vault_send` exigem strict match com o token USDG registrado na sessão.
  - **Verificação:** `is_token_allowed(configured, token)`. Tokens não autorizados revertem com `NotVaultAuthorized` ou `TokenTransferFailed`.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`

- [ ] **Contabilidade do Teto Diário & Reembolso Rolante (24h)**
  - **Invariante:** Janela deslizante de 24 horas (`DAILY_WINDOW_SECS = 86400`). Reembolsos em `refund_disputed` utilizam `current_daily_spent` para avaliar o valor ativo na janela corrente e invocar `restore_daily_spent` sem underflow.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Testes:** `tests::gasto_diario_expira_em_24h`, `tests::refund_restaura_teto_diario_corretamente`

- [ ] **Proteção contra Overflow / Conversão Segura (`U256` > `u128`)**
  - **Invariante:** Nenhum input malicioso com `U256` pode causar panic.
  - **Verificação:** `amount_fits_u128`, `risk_saturating`, `u64_saturating`. Entradas excedentes retornam erro tipado `AmountTooLarge`.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Teste:** `tests::valor_maior_que_u128_devolve_erro_tipado_nao_panic`

- [ ] **Trava de Reentrância Financeira (`ReentrancyGuard`)**
  - **Invariante:** Métodos com chamadas externas ERC-20 (`escrow_payment`, `release_payment`, `refund_disputed`, `vault_send`) possuem trava explícita de reentrância.
  - **Verificação:** Leitura e mutação do campo `reentrancy_locked`. Chamadas reentrantes revertem com `ReentrancyGuard`.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`

- [ ] **Mutabilidade da Sessão Bloqueada quando Congelada (`SessionFrozenError`)**
  - **Invariante:** Se `session_frozen == true`, nenhuma mutação em política (`init_session`, `log_approval`, `set_usdg_token`, `update_policy`) é permitida, exceto `unfreeze` pelo dono.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`

- [ ] **Controle de Janela de Disputa & Double-Claim**
  - **Invariante:** Disputa dentro de 3 dias (`dispute_deadline_of`). Liberar após deadline bloqueia refund (`AlreadyReleased`). Refund do guardião bloqueia release (`AlreadyRefunded`).
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Teste:** `tests::disputa_tem_prazo_de_tres_dias`

- [ ] **Verificação WASM & ABI**
  - **Comando:** `cd zeus-guard-contract && cargo stylus check`
  - **Tamanho:** Artefato WASM 23,4 KiB (23.939 bytes).

---

## 2. Motor de Risco QCSN & Benchmark de Dados Reais

- [ ] **Features Causais Sem Vazamento Temporal**
  - **Invariante:** Nenhuma feature consulta blocos futuros (`block <= tx.block`). Frequências e métricas são acumuladas rigorosamente até o bloco atual.
  - **Arquivo:** `engine/realdata_benchmark.py`, `engine/real_features.py`

- [ ] **Rotulagem Neutra por Desfecho On-Chain**
  - **Separação:** `ATTACK` (drenagem confirmada <= 4h em EOA/unverified), `BENIGN` (interações normais/DEXs), `pulled_by_third_party` (contagem bruta).
  - **Arquivo:** `engine/data/label_by_outcome.py`

- [ ] **Equivalência Matemática Quench vs Argmin**
  - **Invariante:** 0 divergências entre o seletor quench e o argmin determinístico em 1.863 casos de teste.
  - **Comando:** `python3 engine/honesty_experiment.py`

- [ ] **Métricas no Dataset Real (Arbitrum Mainnet)**
  - **Comando:** `python3 engine/realdata_benchmark.py`
  - **Resultados:** 81 eventos rotulados (14 ataques, 67 benignos). Recall = 100,0% (14/14), Taxa de Falsos Alarmes = 11,9% (8/67), Acurácia Global = 90,1%.

---

## 3. Extensão MV3 & Hook EIP-1193

- [ ] **Injeção Antecipada (`document_start`)**
  - **Invariante:** Intercepta `window.ethereum` antes dos scripts do dApp carregarem.
  - **Arquivo:** `ext/manifest.json`, `ext/content.js`, `ext/zeus_hook.js`

- [ ] **Verificação On-Chain de Permits EIP-712**
  - **Invariante:** Consulta `approval_status_pub` no contrato ZEUS v4 antes da assinatura. Spenders revogados resultam no cancelamento da assinatura sem invocar a carteira.
  - **Arquivo:** `ext/zeus_hook.js`

- [ ] **Respostas de Erro EIP-1193 Padrão (Código 4001)**
  - **Invariante:** Rejeições e cancelamentos retornam erro padrão 4001 para a aplicação dApp.
  - **Arquivo:** `ext/zeus_hook.js`

- [ ] **Comportamento quando o Guardião/RPC Falha**
  - **Modos:** `FAIL_OPEN` (avisa via banner e prossegue) e `FAIL_CLOSED` (bloqueia com erro 4001).
  - **Suíte de Testes (Node.js):** `node ext/test_extension.js` (7/7 pass).

---

## 4. Integração & Smoke Tests On-Chain (Arbitrum Sepolia)

- [ ] **Endereço Canônico Deploaiado:** `0xa9ef4e9be0e8f45e737f361380743faab72fe76a`
- [ ] **Suíte Smoke v4:** `python3 proof/smoke_v4.py` (13/13 passadas)
- [ ] **Simulação de Ataque & Defesa Vivo:** `python3 proof/live_attack_defense.py --rpc https://sepolia-rollup.arbitrum.io/rpc --contract 0xa9ef4e9be0e8f45e737f361380743faab72fe76a --victim 0x1718bd9000B81bD5996DeE981eb76232bc2438B3` (4/4 passadas)

---

## 5. Portões Restantes para Mainnet

- [ ] Auditoria formal externa concluída por empresa especializada de segurança de smart contracts Rust/Stylus.
- [ ] Configuração de chave de produção dedicada / contrato multisig para owner e guardião.
- [ ] Validação formal de redeploy em Mainnet.
