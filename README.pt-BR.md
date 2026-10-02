# ⚡ ZEUS GUARD — Firewall Pré-Transação para Traders Varejo e Pagamentos Agênticos

> **O Antivírus On-Chain do Trader Varejo e Agentes Autônomos:** Um firewall pré-transação operando na camada do provedor EIP-1193 que intercepta drainers **antes da criação da assinatura**, combinado com um registro público de revogação (`approval_status_pub`), um cofre de custódia USDG com janela de desafio configurável (≥120s) e um disjuntor de emergência — movido por um **motor de risco determinístico de sub-milissegundo** — classificador argmin 100% determinístico em produção, sem componentes probabilísticos ou executados em hardware quântico (a origem de pesquisa em redes de spins é documentada, não invocada em runtime).
>
> **Zero matemática misteriosa, zero quântico enganoso:** O motor de produção utiliza um classificador argmin determinístico e auditável (<0,1 ms/tx) comprovado 100% equivalente (0 divergências em 1.848 casos de teste) ao modelo de quench quântico dissipativo.

**Autor:** Clebson Campos de Araújo (Clebson Scott) · Arbitrum Open House Singapore 2026 · Buildathon
**Repositório:** https://github.com/clebson-scott/zeus-guard · **Landing:** https://telegra.ph/ZEUS-GUARD--Pre-Transaction-Firewall-for-Everyday-Traders-09-26

---

## 🎯 RESUMO — Estado Atual e Métricas Verificadas da Release (v6 hardened — canônico; v4 = RC congelada para auditoria que alimenta as demos web)

| Componente | Status & Métricas Verificadas | Evidência / Artefato |
|---|---|---|
| **Contrato Stylus Deployed (v4)** | Ativo na Arbitrum Sepolia (`421614`) · Tamanho WASM: **23,4 KiB** | [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a) |
| **Testes Nativos em Rust** | **15/15 PASSANDO** (autorização de cofre, restrição de token, restauração de teto diário 24h, reentrância, imutabilidade sob congelamento, prazo de disputa, erro tipado `AmountTooLarge`) | `cd zeus-guard-contract && cargo test` |
| **Extensão MV3 & Hook EIP-1193** | **10/10 PASSANDO** (injeção antecipada em `document_start`, validação de permit EIP-712, cancelamento pré-carteira com erro 4001, modos `FAIL_OPEN` e `FAIL_CLOSED`) | `node ext/test_extension.js` |
| **Motor QCSN & Experimento de Honestidade** | **0 divergências quench vs argmin** em **1.848 casos de teste**; latência analítica **<0,1 ms/tx** | `python3 engine/honesty_experiment.py` |
| **Benchmark em Dados Reais** | **81 eventos reais da Arbitrum**: **100,0% Recall** (14/14 drainers bloqueados), **11,9% Taxa de FP** (redução vs 89,6% baseline), **90,1% Acurácia Global** | `python3 engine/realdata_benchmark.py` |
| **Smoke Tests On-Chain (v4)** | **13/13 PASSANDO** na Arbitrum Sepolia | `python3 proof/smoke_v4.py` |
| **Prova de Ataque & Defesa Vivo** | **4/4 PASSANDO** ao vivo contra o contrato | `python3 proof/live_attack_defense.py` |
| **CI Automatizado** | Pipeline cobrindo Stylus Rust (15/15), motor Python e testes da extensão Node | `.github/workflows/ci.yml` |
| **Pacote de Auditoria** | Pacote completo pronto para revisão externa | [`JUDGE_SUBMISSION.md`](JUDGE_SUBMISSION.md) · [`docs/AUDIT_CHECKLIST.md`](docs/AUDIT_CHECKLIST.md) · [`SECURITY.md`](SECURITY.md) · [`REAL_DATA.md`](REAL_DATA.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/MATH.md`](docs/MATH.md) |

---

## 💡 O Problema Central: Por Que a Segurança Web3 Falha com o Usuário Varejo

Traders pessoa física e agentes autônomos perdem milhões para assinaturas de drainers, aprovações maliciosas ERC-20 (`approve(spender, max)`) e permits EIP-712 disfarçados (`permit(...)`). As causas são estruturais:

1. **Assinatura Cega:** Interfaces de carteiras exibem hexadecimais brutos ou contratos não verificados. Usuários não técnicos não conseguem distinguir uma DEX legítima de um drainer.
2. **Imutabilidade Pós-Assinatura:** Assim que uma assinatura ou permit é concedido, a execução é imediata na blockchain. Alertadores e exploradores pós-fato apenas registram a perda.
3. **Toxicidade das Aprovações:** Aprovações ilimitadas permanecem abertas indefinidamente, permitindo que atacantes drenem fundos meses após a interação inicial.

---

## 🛡️ Defesa Pré-Carteira: Por Que a Proteção Deve Ocorrer ANTES da Carteira

Ao contrário das ferramentas tradicionais que simulam transações *depois* que a tela da carteira é aberta ou emitem alertas pós-fato, **o ZEUS GUARD atua antes da criação da assinatura**:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ 1. Requisição do dApp (eth_sendTransaction / eth_signTypedData / permit)          │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ 2. Hook de Extensão Pré-Carteira EIP-1193 (ext/zeus_hook.js @ document_start)    │
│    • Intercepta a chamada RPC ANTES que o modal do MetaMask / Rabby seja exibido │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    ▼                                         ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│ 3a. Motor de Risco QCSN (<0,1 ms/tx)  │ │ 3b. Consulta de Estado On-Chain       │
│     • Vetor de features x ∈ [0,1]⁸    │ │     • Consulta Contrato Stylus v4     │
│     • Distância de arquétipos & Gibbs │ │       approval_status_pub(user,     │
│     • Veredicto: LIBERAR/ALERTAR/   │ │       spender)                        │
│       BLOQUEAR                        │ │                                       │
└───────────────────┬───────────────────┘ └───────────────────┬───────────────────┘
                    │                                         │
                    └────────────────────┬────────────────────┘
                                         │
               ┌─────────────────────────┴─────────────────────────┐
               │ Risco ≥ 6000 OU Spender Revogado OU Limite Diário?│
               └────────────┬─────────────────────────┬────────────┘
                            │ SIM                     │ NÃO
                            ▼                         ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────┐
│ 🛑 REJEITA NA CAMADA DO PROVEDOR      │ │ 🟢 ENCAMINHA PARA A CARTEIRA          │
│    • Lança Erro EIP-1193 Código 4001 │ │    • Tela da carteira abre normalmente│
│    • Modal da carteira NUNCA abre     │ │    • Usuário assina transação legítima│
│    • NENHUMA assinatura é gerada      │ │    • Entra no Cofre USDG se aplicável  │
└───────────────────────────────────────┘ └───────────────────────────────────────┘
```

Ao interceptar no nível do provedor (`window.ethereum`), o ZEUS GUARD impede a geração da assinatura em caso de ataque ou aprovação revogada, retornando o código de cancelamento padrão EIP-1193 `4001`.

---

## ⚡ Por Que Isso É Diferente (Why This Is Different)

*Diferenciais de engenharia reais e transparentes, sem promessas vazias:*

1. **Hook Pré-Assinatura vs Alertas Pós-Assinatura:** Intercepta requisições RPC na camada do provedor `EIP-1193` em `document_start`. Impede a criação da assinatura antes que o modal da carteira abra, em vez de alertar após o clique ou registrar após a perda.
2. **Motor de Política On-Chain vs Caixa-Preta Off-Chain:** A pontuação off-chain é consultiva; o contrato Stylus WASM na Arbitrum (`0xa9ef...`) é a lei imutável na chain impondo teto de risco de 60%, limite diário rolante de 24h, congelamento de sessão, registro público de revogação (`approval_status_pub`) e janela de desafio no cofre USDG (≥120s).
3. **Matemática Transparente & Zero Quântico Enganoso:** O classificador de risco foi idealizado originalmente com protocolos de quench dissipativo em Redes Quânticas de Spins Contínuos (QCSN). Para obter latência sub-milissegundo (<0,1 ms/tx), a produção executa um argmin analítico determinístico exato. Provamos 0 divergências entre quench e argmin em 1.848 casos de teste (`engine/honesty_experiment.py`) e mantemos a validação em hardware quântico (`ibm_fez`) como pesquisa aberta, servindo código CPU ultrarrápido e auditado em produção.
4. **Fundamentação Empírica em Dados Reais:** Testado contra 81 eventos reais de `Approve` da Arbitrum Mainnet (100,0% de recall em drainers, 11,9% de falsos positivos contra 89,6% do baseline) com causalidade estrita sem vazamento temporal (`block <= tx.block`).

---

## 🏛️ Arquitetura do Sistema e Camada de Aplicação On-Chain

| Módulo | Função | Camada de Execução |
|---|---|---|
| **Firewall Pré-Transação** | Analisa cada transação e permit antes da assinatura; bloqueia drainers (`TooRisky`) e violações de limite (`AboveDailyCap`). | Extensão MV3 (`zeus_hook.js`) & Contrato Stylus (`check_tx`) |
| **Registro de Revogação Pública (`approval_status_pub`)** | Expõe na chain o estado do approval e revogação para leitura por carteiras antes de assinar. | Contrato Stylus v4 & Hook EIP-712 |
| **Cofre de Custódia USDG** | Retém pagamentos via `IERC20.transferFrom` por uma janela de desafio (≥120s). | Contrato Stylus (`escrow_payment` / `vault_send`) |
| **Disputa & Reembolso do Guardião** | Permite contestação pelo guardião e reembolso imediato à vítima (`refund_disputed`) restaurando o limite ativo. | Contrato Stylus (`dispute_payment` / `refund_disputed`) |
| **Disjuntor de Emergência** | Congela a sessão do usuário (`session_frozen`) impedindo qualquer mutação no contrato em caso de ataque. | Contrato Stylus (`freeze_session`) |

### O Papel Real On-Chain (Arbitrum Stylus WASM v4)

O contrato inteligente não é um registrador passivo; é a **máquina de estados imutável da política de segurança**:
- **`check_tx(user, amount, risk_x100)`**: Valida a pontuação de risco contra `RISK_BLOCK_X100` (6000 = 60%), verifica a sessão, checa o gasto ativo da janela rolante de 24h (`current_daily_spent`) e reverte em caso de violação (`TooRisky`, `AboveDailyCap`, `SessionFrozen`, `NoSession`).
- **`approval_status_pub(user, spender)`**: Mapeamento público consultável por extensões e dApps para verificar se um spender foi revogado (`guardian_revoke`).
- **`escrow_payment` & `vault_send`**: Executa a custódia real de tokens USDG ERC-20 via `IERC20.transferFrom`, mantendo a retenção por no mínimo 120 segundos (`MIN_CHALLENGE_WINDOW`).
- **`dispute_payment` & `refund_disputed`**: Permite que o guardião conteste transferências suspeitas durante a janela e reembolse os tokens para a vítima, restaurando com segurança o teto diário rolante (`restore_daily_spent`).

---

## ⚛️ O Motor de Risco QCSN: Origem de Pesquisa Quântica & Motor em Produção

### Origem de Pesquisa vs. Motor Analítico em Produção
1. **Origem de Pesquisa (Continuous Spin Network):** O classificador modela fronteiras de decisão como dinâmica de spins sob quench dissipativo em banho térmico (60 passos de annealing, β: 2→40). O mecanismo foi medido experimentalmente no processador quântico **IBM Quantum `ibm_fez`** (job `daorvfg2fm4c73f5tlog`, fidelidade de seleção 0.997).
2. **Motor de Produção (Caminho Analítico Argmin):** Para interceptação em sub-milissegundo (<0,1 ms/tx), a produção calcula a decisão por seleção de arquétipo mais próximo (argmin sobre distância quadrática) com distribuição exata de Gibbs em β = 40.
3. **Prova de Equivalência (`engine/honesty_experiment.py`):**
   - Testados 1.848 casos de teste entre benchmarks sintéticos, ruído de estresse (σ = 0.05, 0.15, 0.30) e pontos médios exatos.
   - Resultado: **0 divergências entre quench e argmin**. O quench atinge exatamente a mesma decisão do argmin com 276x mais custo computacional. A produção utiliza o caminho argmin rápido em CPU com transparência.

### Benchmark em Dados Reais (`python3 engine/realdata_benchmark.py`)

- **Dataset:** 81 eventos reais de `Approve` coletados da Arbitrum Mainnet, rotulados estritamente pelo desfecho on-chain sem vazamento temporal (`block <= tx.block`).
- **Ataques Capturados (Recall):** **14/14 (100,0% Recall)** — 10 bloqueios diretos (`BLOQUEAR`), 4 alertas preventivos (`ALERTAR`).
- **Taxa de Falsos Positivos:** **11,9% (8/67 benignos)**, em comparação com **89,6%** do baseline "approve ilimitado / EOA".
- **Acurácia Global:** **90,1% (73/81 classificados corretamente)**.

---

## 📊 Métricas Verificadas & Limitações Declaradas

### Matriz de Métricas Verificadas
- **Tamanho do Contrato:** 23,4 KiB WASM compilado via Rust Stylus (`cargo stylus check`).
- **Cobertura de Testes Unitários:** 15/15 testes Rust passando (`cargo test`).
- **QA da Extensão:** 10/10 testes Node.js passando (`node ext/test_extension.js`).
- **Smoke Tests On-Chain:** 13/13 passando na Arbitrum Sepolia (`python3 proof/smoke_v4.py`).
- **Ataque e Defesa Vivo:** 4/4 passando na testnet contra o contrato ativo (`python3 proof/live_attack_defense.py`).

### Limitações Verificadas (Declaradas e Transparentes)
1. **Taxa de Falsos Positivos (11,9%):** 8 em 67 aprovações legítimas (como contratos novos ou roteadores DEX não verificados) geraram alerta de risco (`ALERTAR`). É um tradeoff intencional para garantir 100% de recall em ataques.
2. **Latência de Custódia (Janela de Desafio ≥120s):** O cofre introduz retenção mínima de 120 segundos para liberação do pagamento. O design é otimizado para transferências varejo e liquidações agênticas, não para arbitragem de alta frequência (HFT) ou flash loans.
3. **Modos de Fallback da Extensão:** Caso o RPC do motor esteja indisponível, a extensão opera em `FAIL_OPEN` (avisa o usuário e permite a assinatura) por padrão, ou `FAIL_CLOSED` (bloqueia com erro 4001) no modo estrito.
4. **Papel da Execução Quântica:** A execução em hardware QPU é a origem de pesquisa e benchmark de validação, não um endpoint ativo no caminho de transação ao vivo.

---

## 🚀 Comandos Rápidos de Execução e Verificação

```bash
# 1. Executar Testes Nativos do Contrato (15/15 PASS)
cd zeus-guard-contract && cargo test

# 2. Verificar Compilação WASM Stylus (23,4 KiB)
cargo stylus check

# 3. Executar Benchmark Sintético e Experimento de Honestidade (0 divergências)
python3 engine/demo.py
python3 engine/honesty_experiment.py

# 4. Executar Benchmark em Dados Reais da Mainnet (100% Recall, 11,9% FP)
python3 engine/realdata_benchmark.py

# 5. Executar Suíte de Testes da Extensão MV3 (10/10 PASS)
node ext/test_extension.js

# 6. Executar Smoke Tests On-Chain v4 (13/13 PASS)
python3 proof/smoke_v4.py

# 7. Executar Prova de Ataque e Defesa Vivo (4/4 PASS)
python3 proof/live_attack_defense.py --rpc https://sepolia-rollup.arbitrum.io/rpc   --contract 0xa9ef4e9be0e8f45e737f361380743faab72fe76a   --victim 0x1718bd9000B81bD5996DeE981eb76232bc2438B3
```

---

## 🚦 Relatório Final de Prontidão de Release

1. **Pronto Agora na Testnet (Arbitrum Sepolia):**
   - Contrato Stylus v4 ativo em [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a).
   - Todas as suítes de teste passando sem erros (15/15 Rust, 10/10 Node extension, 13/13 smoke on-chain, 4/4 ao vivo, 0 divergências).
2. **Pronto para Auditoria Externa:**
   - Pacote completo compilado em `docs/AUDIT_CHECKLIST.md`, `SECURITY.md`, `REAL_DATA.md`, `docs/ARCHITECTURE.md` e `docs/MATH.md`.
3. **Bloqueado para Mainnet:**
   - Publicação em Mainnet **estritamente bloqueada** até a realização de auditoria externa formal por empresa especializada de segurança e configuração de chave/multisig de produção.
