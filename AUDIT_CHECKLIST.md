# 📋 Checklist de Auditoria e Validação Defensiva — ZEUS GUARD (v4 Release Candidate)

Este checklist orienta a verificação interna concluída e a revisão formal por auditores externos do pacote **ZEUS GUARD v4**. Cada item possui comandos de verificação reproduzíveis, localização no código-fonte e o status de validação.

> 📄 **Relatório Final Consolidado:** Veja o [Relatório Final de Consolidação Red-Team](RELATORIO_FINAL_REDTEAM.md) para a análise detalhada de achados corrigidos, limitações residuais, evidências de testes e separação dos pilares.

---

## 1. Smart Contract (Stylus / Rust v4) — [x] Defesa Interna Concluída

- [x] **Autorização de Cofre e Saque (`vault_send`)**
  - **Invariante:** Apenas o `owner` ou o `guardian` autorizado pode executar saques do cofre.
  - **Verificação:** `is_vault_authorized(sender, owner, guardian)`. Chamadas por terceiros revertem com `NotVaultAuthorized`.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Evidência/Teste:** `tests::vault_send_autorizacao_e_restricao_de_token` (PASS)

- [x] **Restrição de Token Permitido no Cofre (`session_usdg`)**
  - **Invariante:** Transferências e custódia em `escrow_payment` e `vault_send` exigem match estrito com o token USDG registrado na sessão.
  - **Verificação:** `is_token_allowed(configured, token)`. Tokens não autorizados revertem com `NotVaultAuthorized` ou `TokenTransferFailed`.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Evidência/Teste:** `tests::vault_send_autorizacao_e_restricao_de_token` (PASS)

- [x] **Contabilidade do Teto Diário & Reembolso Rolante (24h)**
  - **Invariante:** Janela deslizante de 24 horas (`DAILY_WINDOW_SECS = 86400`). Reembolsos em `refund_disputed` utilizam `current_daily_spent` para avaliar o valor ativo na janela corrente e invocar `restore_daily_spent` sem underflow.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Evidência/Testes:** `tests::gasto_diario_expira_em_24h`, `tests::refund_restaura_teto_diario_corretamente` (PASS)

- [x] **Proteção contra Overflow / Conversão Segura (`U256` > `u128`)**
  - **Invariante:** Nenhum input malicioso com `U256` causa panic ou overflow.
  - **Verificação:** `amount_fits_u128`, `risk_saturating`, `u64_saturating`. Entradas excedentes retornam erro tipado `AmountTooLarge`.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Evidência/Teste:** `tests::valor_maior_que_u128_devolve_erro_tipado_nao_panic` (PASS)

- [x] **Trava de Reentrância Financeira (`ReentrancyGuard`)**
  - **Invariante:** Métodos com chamadas externas ERC-20 (`escrow_payment`, `release_payment`, `refund_disputed`, `vault_send`) possuem trava explícita de reentrância.
  - **Verificação:** Leitura e mutação do campo `reentrancy_locked`. Chamadas reentrantes revertem com `ReentrancyGuard`.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Evidência/Teste:** Reentrancy guard test em `lib.rs` (PASS)

- [x] **Mutabilidade da Sessão Bloqueada quando Congelada (`SessionFrozenError`)**
  - **Invariante:** Se `session_frozen == true`, nenhuma mutação em política (`init_session`, `log_approval`, `set_usdg_token`, `update_policy`) é permitida, exceto `unfreeze` pelo dono.
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Evidência/Teste:** Session freeze verification (PASS)

- [x] **Controle de Janela de Disputa & Double-Claim**
  - **Invariante:** Disputa dentro de 3 dias (`dispute_deadline_of`). Liberar após deadline bloqueia refund (`AlreadyReleased`). Refund do guardião bloqueia release (`AlreadyRefunded`).
  - **Arquivo:** `zeus-guard-contract/src/lib.rs`
  - **Evidência/Teste:** `tests::disputa_tem_prazo_de_tres_dias` (PASS)

- [x] **Verificação WASM & ABI Stylus v4**
  - **Comando:** `cd zeus-guard-contract && cargo stylus check`
  - **Tamanho:** Artefato WASM 23,4 KiB (23.939 bytes) validado contra RPC Arbitrum Stylus.

---

## 2. Motor de Risco QCSN & Benchmark de Dados Reais — [x] Defesa Interna Concluída

- [x] **Features Causais Sem Vazamento Temporal**
  - **Invariante:** Nenhuma feature consulta blocos futuros (`block <= tx.block`). Frequências e métricas são acumuladas rigorosamente até o bloco atual.
  - **Arquivo:** `engine/realdata_benchmark.py`, `engine/real_features.py`
  - **Evidência:** Invariant Test 1 & 5 (PASS)

- [x] **Rotulagem Neutra por Desfecho On-Chain**
  - **Separação:** `ATTACK` (drenagem confirmada <= 4h em EOA/unverified), `BENIGN` (interações normais/DEXs/roteadores legítimos).
  - **Arquivo:** `engine/data/label_by_outcome.py`, `engine/data/real_labeled_approves.json`
  - **Evidência:** Reclassificação de roteadores DEX para BENIGN e validação semântica das labels.

- [x] **Equivalência Matemática Quench vs Argmin & Estabilidade Numérica**
  - **Invariante:** 0 divergências entre o seletor quench e o argmin determinístico em 1.848 casos de teste. Tratamento de overflow via `np.clip(beta * dE0, -700, 700)` e normalização de array de probabilidades.
  - **Comando:** `python3 engine/honesty_experiment.py`
  - **Evidência:** 0/1848 divergências, aceleração analítica de 303x (<0.003 ms/tx).

- [x] **Métricas no Dataset Real (Arbitrum Mainnet)**
  - **Comando:** `python3 engine/realdata_benchmark.py`
  - **Resultados:** 81 eventos rotulados (14 ataques, 67 benignos). Recall = 100,0% (14/14), Taxa de Falsos Alarmes = 11,9% (8/67), Acurácia Global = 90,1%.

- [x] **Suíte de Invariantes Automática**
  - **Comando:** `python3 engine/test_engine_invariants.py`
  - **Resultados:** 5/5 testes de invariantes (equivalência, normalização, estabilidade extrema, monotonicidade, integridade do dataset) PASSOU.

---

## 3. Extensão MV3 & Hook EIP-1193 — [x] Defesa Interna Concluída

- [x] **Injeção Antecipada (`document_start`) & Trap de Provedor**
  - **Invariante:** Intercepta `window.ethereum` antes dos scripts do dApp carregarem usando `Object.defineProperty` setter trap, escuta EIP-6963 e polling de 20ms.
  - **Arquivo:** `ext/manifest.json`, `ext/content.js`, `ext/zeus_hook.js`
  - **Evidência:** `test_extension.js` Teste 1 & Teste 8 (PASS)

- [x] **Verificação On-Chain de Permits EIP-712 / Permit2 / On-chain**
  - **Invariante:** Consulta `approval_status_pub` no contrato ZEUS v4 antes da assinatura. Spenders revogados resultam no cancelamento da assinatura sem invocar a carteira.
  - **Arquivo:** `ext/zeus_hook.js`
  - **Evidência:** `test_extension.js` Teste 3, Teste 9 e Teste 10 (PASS)

- [x] **Respostas de Erro EIP-1193 Padrão (Código 4001)**
  - **Invariante:** Rejeições e cancelamentos retornam erro padrão 4001 para a aplicação dApp sem chamar a carteira subjacente.
  - **Arquivo:** `ext/zeus_hook.js`
  - **Evidência:** `test_extension.js` Testes 2, 3, 5, 7, 9, 10 (PASS)

- [x] **Comportamento quando o Guardião/RPC Falha (`FAIL_OPEN` / `FAIL_CLOSED`)**
  - **Modos:** `FAIL_OPEN` (avisa via banner e prossegue) e `FAIL_CLOSED` (bloqueia com erro 4001).
  - **Suíte de Testes (Node.js):** `node ext/test_extension.js` (10/10 PASS)

---

## 4. Integração & Smoke Tests On-Chain (Arbitrum Sepolia) — [x] Defesa Interna Concluída

- [x] **Endereço Canônico Deployado (v4):** `0xa9ef4e9be0e8f45e737f361380743faab72fe76a`
- [x] **Suíte Smoke v4:** `python3 proof/smoke_v4.py` (13/13 passadas)
- [x] **Simulação de Ataque & Defesa Vivo:** `python3 proof/live_attack_defense.py --rpc https://sepolia-rollup.arbitrum.io/rpc --contract 0xa9ef4e9be0e8f45e737f361380743faab72fe76a --victim 0x1718bd9000B81bD5996DeE981eb76232bc2438B3` (4/4 passadas)

---

## 5. Portões Restantes para Auditoria Externa & Mainnet

### A. Auditoria Externa Pendente
- [ ] **Engajamento de Empresa Especializada:** Submissão do pacote v4 audit-ready para empresa terceirizada de auditoria de smart contracts Rust/Stylus.
- [ ] **Revisão Formal de Código Stylus/WASM:** Auditoria independente das invariantes do contrato e geração do relatório externo de segurança.
- [ ] **Remediação de Achados Externos:** Resolução de quaisquer achados apontados pelos auditores externos antes do deploy de produção.

### B. Portões de Implantação em Mainnet (Mainnet Deployment Gates)
- [ ] **Relatório de Auditoria Externa Assinado:** Certificação final sem vulnerabilidades críticas ou de alta severidade abertas.
- [ ] **Gestão de Chaves de Produção:** Configuração de carteira multisig / Timelock para os papéis de `owner` e `guardian` em ambiente de produção (Arbitrum One Mainnet).
- [ ] **Infraestrutura RPC de Altíssima Disponibilidade:** Servidores RPC primários e de backup com redundância regional para o guardião e a extensão.
- [ ] **Deploy e Verificação em Arbitrum Mainnet:** Script de deploy automatizado e verificação de código-fonte on-chain no Arbiscan Mainnet.
