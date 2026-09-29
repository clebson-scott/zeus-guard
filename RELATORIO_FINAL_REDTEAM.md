# 🛡️ Relatório Final de Consolidação Red-Team & Validação Defensiva — ZEUS GUARD v4

## 1. Visão Geral e Resumo Executivo

- **Projeto:** ZEUS GUARD v4 (Arbitrum Stylus + Motor QCSN + Extensão Browser MV3)
- **Data da Consolidação:** 27 de Setembro de 2026
- **Status da Defesa Interna:** 100% Concluída (15/15 unit tests, 5/5 invariant tests, 10/10 extension tests, 13/13 smoke tests on-chain, 4/4 live attack-defense proofs, 40.054 entradas adversariais no fuzz harness com 0 falhas)
- **Revisão v4.5 (28/09/2026):** camada de identidade integrada (Blockscout, sem chave), ground truth v2 corrigido (ataques verdadeiros: 54, recall 100% preservado, FP 14,4% → 12,6%), split temporal validado (recall estável, FP com gradiente de warm-up documentado), INV9 receiver-match em produção (33/33).
- **Status de Auditoria Externa:** PENDENTE (Engajamento e certificação formal de terceiros)
- **Status de Implantação em Mainnet:** BLOQUEADO por Gates de Produção (Sem deploy em Mainnet, sem chaves de produção)

---

## 2. Consolidação dos Resultados por Frente de Trabalho

### 2.1 Smart Contract (Stylus / Rust v4) — `redteam_contrato`
- **Contrato Deployado em Sepolia:** `0xa9ef4e9be0e8f45e737f361380743faab72fe76a`
- **Tamanho WASM:** 23,4 KiB (23.939 bytes) — `cargo stylus check` PASSOU
- **Suíte de Testes Unitários Nativos:** 15/15 PASSOU (`cargo test`)
- **Análises Realizadas:**
  - Autorização de cofre e saques (`vault_send`)
  - Verificação de token USDG permitido (`session_usdg`)
  - Teto diário de gastos com janela móvel de 24h e refund resiliente (`refund_disputed`)
  - Tratamento de conversão `U256` > `u128` sem panics, retornando erro tipado (`AmountTooLarge`)
  - Proteção de reentrância em chamadas externas ERC-20 (`ReentrancyGuard`)
  - Congelamento de sessão e imutabilidade de políticas (`session_frozen`)
  - Prazos e regras anti-double claim em disputas (`dispute_deadline_of`, `AlreadyReleased`, `AlreadyRefunded`)
- **Vulnerabilidades Não Tratadas:** Nenhuma vulnerabilidade crítica ou não tratada remanescente no contrato.

### 2.2 Motor de Risco QCSN & Dataset Real — `redteam_motor`
- **Benchmarking de Dados Reais:** v2 ESCALADO: 15.291 eventos rotulados da Arbitrum Mainnet (527 ataques em 82 campanhas distintas, 14.764 benignos) — 189x o dataset original
- **Recall de Ataques:** 100,0% (14/14 ataques capturados — 10 bloqueios diretos, 4 alertas preventivos)
- **Taxa de Falsos Alarmes (FP):** 11,9% (8/67 benignos) | **Acurácia Global:** 90,1%
- **Experimento de Honestidade (Quench vs Argmin):** 0/1.848 divergências entre o seletor quench e o caminho analítico argmin (<0,003 ms/tx, aceleração de ~300x).
- **Invariantes Automáticas:** 5/5 PASSOU em `engine/test_engine_invariants.py`.


- **Rigor Estatístico (Intervalos de Confiança Wilson, 95%):**
  - Recall de ataques: 100,0% observado — IC95% = **[78,5%, 100%]** com n=14 ataques. O recall pontual é perfeito, mas a amostra impõe limite inferior de ~78,5%; ampliação do dataset é prioridade declarada do Pilar de dados.
  - Taxa de falsos alarmes: 11,9% — IC95% = **[6,2%, 21,8%]** (n=67).
  - Acurácia global: 90,1% — IC95% = **[81,7%, 94,9%]** (n=81).
  - Baseline honesto incluído ('ilimitado em EOA': recall 85,7%, FP 0,0%) para contextualizar o trade-off do motor.

- **Benchmark Escalado v2 (15.291 eventos reais, ~74 min de chain):**
  - **Recall de Ataques:** 100,0% (527/527 — 58 bloqueios diretos, 469 alertas preventivos) — **IC95% Wilson = [99,3%, 100%]** (v1 com n=14: [78,5%, 100%]).
  - **Taxa de Falsos Alarmes (FP):** 14,4% (2.123/14.764) | IC95% = [13,8%, 15,0%] | **Acurácia Global:** 86,1%.
  - **Metodologia de Ground Truth Refinada (red-team v4.2):** rotulagem por desfecho + três filtros anti-contaminação verificados por pesquisa em block explorers: (a) lista ampliada de 14 protocolos legítimos (Permit2, OKX DEX, GMX V2, Aave, CoW Relayer, Across Bridge, Seaport conduit, Tracer, + os 5 originais); (b) regra bot-infra: spender contrato com 1 único owner = operação própria, não ataque; (c) exigência de múltiplas vítimas por spender (10–36 owners nas campanhas remanescentes).
  - **Achado de Red-Team na própria coleta:** 4.629 eventos (30%) rotulados como ataque pela regra bruta eram, na verdade, infraestrutura legítima major (Permit2, OKX, GMX, Aave, CoW, Across, routers DEX) e bots próprios de market-making — approve ilimitado + pull por terceiro é INSEPARÁVEL do uso normal de DEXs sem verificação de identidade. Este achado é evidência de que a curadoria v1 (81 eventos) escondia um viés metodológico que só a escala revelou.

### 2.3 Extensão MV3 & Hook EIP-1193 — `extensao_qa_defensivo`
- **Captura Antecipada:** Injeção em `document_start` com `all_frames: true` e `Object.defineProperty` trap na propriedade `window.ethereum`, suporte a EIP-6963 e polling de 20ms.
- **Intercepção de Permits:** Consulta on-chain em `approval_status_pub` para EIP-712 / Permit2 / On-chain permits antes de qualquer janela de assinatura.
- **Respostas Padrão EIP-1193:** Código de erro standard 4001 em rejeições/bloqueios sem invocar o método da carteira.
- **Modos de Tolerância a Falhas:** `FAIL_OPEN` (padrão com banner explicativo) e `FAIL_CLOSED` (opcional via flag/storage).
- **Suíte de Testes Automatizada:** 10/10 PASSOU em `node ext/test_extension.js`.

### 2.4 CI, Documentação & Reprodutibilidade — `revisao_ci_docs`
- **Sincronização de Artefatos:** `docs/JUDGE_VERIFICATION.md`, `deploy/DEPLOYADO_V4_ARBITRUM_SEPOLIA.md`, `README.md`, `README.pt-BR.md`, `AUDIT_CHECKLIST.md` e `demo/wallet.html` totalmente alinhados em relação a endereços de contrato, tamanho do WASM, Chain ID da Arbitrum Sepolia (`0x66eee`) e dependências do ambiente (`requirements.txt`).
- **Verificação local:** `git diff --check` sem erros.

---

### 2.5 Case Study Forense: "Permit2Proxy" — Falso Positivo e o Golpe por Intents (28/09/2026)

Forense profunda em tráfego suspeito da Arbitrum levou a um alerta inicial ERRÔNEO (contrato tido como drainer de ~US$ 500k) e sua correção pela reengenharia completa: o contrato `0x89c6340b1a1f4b25d36cd8b063d49045caf3f818` é o **Permit2Proxy OFICIAL da LI.FI** (v1.0.4, implantação create2 multi-chain, presente em Avalanche desde 07/2025, labeled "LI.FI: Permit2 Proxy 2" no Etherscan) processando **tráfego legítimo do Jumper Exchange** (443k USDC + 42k USDT0/dia). A tx das "vítimas" decodificada: permit EIP-2612 + bridge com integrator `jumper.exchange`, receiver = **o próprio remetente**, taxa 0,01% — bridge normal.

**O que a reengenharia revelou de verdadeiro valor:**
1. **INV8 como proposta era INCORRETA** — approve+transferFrom atômico é assinatura do fluxo gasless legítimo (EIP-2612/Permit2), não de dreno. Bloquearia todo o tráfego do Jumper. Falso positivo estrutural de qualquer motor baseado em "pull por terceiro".
2. **O golpe real desta classe é o phishing por intents (caso "Axioraswap")**: sites falsos usam a API/contratos OFICIAIS da LI.FI e constroem intents onde o campo `receiver` aponta para a carteira do golpista na chain de destino. Invisible à rotulagem por desfecho on-chain — o crime vive só no parâmetro do calldata.
3. **INV9 (receiver-match) recomendada → IMPLEMENTADA** (`engine/inv9_receiver_match.py`, 33/33 testes): vereditos PASS/ALERT/INDETERMINADO em duas camadas (request autoritativa; calldata com decoders verificados Across V3). Evidência empírica adicional: nas 3 rotas intent da LI.FI o receiver NUNCA viaja em texto puro no calldata — apenas como keccak256(receiver‖sal), words 3-4 — logo a camada calldata é cega para intents e o veredito honesto é INDETERMINADO, com decisão na camada request. PoC ao vivo: golpe → ALERT com flag `deceptive_display` (a resposta exibe a carteira da vítima como destino). Detalhes: `docs/CASE_STUDY_INV9_PHISHING_INTENTS.md`.
4. Campanhas de apoio reclassificadas: `0x26ab7cdf` = operador de tokens homoglifo ("ÚЅDС" cirílico) / dusting em massa; `0x0e9c1a3a` = sonda de allowances (transferFrom de zero).

Detalhes completos em `docs/CASE_STUDY_PERMIT2PROXY_DRAINER.md`.


### 2.6 Camada de Identidade: Correção do Ground Truth v2 e Split Temporal (28/09/2026, revisão v4.5)

**Módulos entregues:** `engine/label_resolver.py` (resolvedor de labels, 17/17 testes) e
`engine/realdata_benchmark_gt_corrected.py` (GT corrigido). Fonte de identidade:
Blockscout Arbitrum/Ethereum (API aberta, sem chave) com whitelist curada + cache
durável auditável (`engine/data/label_cache.json`, 567 spenders do dataset resolvidos).

**Achado (correção de segunda ordem sobre o achado v2):** após a limpeza v2
(4.629 eventos), **473 dos 527 eventos ATTACK remanescentes ainda tinham spender que
é contrato VERIFICADO e nomeado** (Curve tricrypto, Uniswap V2, 1inch AllowanceHolder,
Across SpokePoolPeriphery, CoW, Bebop, Camelot, Morpho, HyperliquidDepositor etc.) —
todos com `verified_protocol=False` na coleta. A verificação de identidade da coleta
falhou para eles e a whitelist de 14 protocolos era insuficiente: a realidade da janela
tem **350+ contratos verificados**. Swaps normais via router (pull por terceiro =
swap executado) permaneceram rotulados como ataques.

**Ground truth corrigido (conservador: exclusão, não re-rotulagem):**
- Ataques verdadeiros: **54** (não 527) em **20 campanhas**, 22 owners-vítima.
- Todos mantêm o perfil clássico: spender contrato NÃO-verificado ou EOA + pull.
- **[B] Motor padrão, GT corrigido:** recall **100% (54/54)**, IC95 = [93,4%, 100%] | FP 14,4% | acurácia 85,7%.
- **[C] Motor + camada de identidade ON:** recall **100% (54/54)** | FP **12,6%** (−1,8 p.p. sem perder um único ataque) | acurácia 87,5%.
- Painel [A] (v2 publicado, GT contaminado) mantido no output para transparência: recall 100% "527/527" era inflado por contaminação de rótulo.
- Recibo: `evidence/realdata_benchmark_gt_corrected.json`.

**Split temporal (validação de estabilidade, `engine/realdata_benchmark_temporal.py`):**
- Janela ~74 min de chain dividida no bloco mediano; features seguem CAUSAIS (sem consulta a blocos futuros).
- **Recall 100% nas DUAS metades** (FN=0) no GT corrigido (25 ataques na inicial, 29 na final).
- **FP não é estável: 18,0% → 10,7%** entre metades (IC95 não se sobrepõem) — artefato de
  warm-up da feature causal de frequência de token no início da janela, não drift de
  comportamento. Implicação honesta: o FP agregado de 14,4% tem gradiente temporal; a
  métrica exige janela de warm-up ou normalização por idade do evento.
- Recibos: `evidence/realdata_benchmark_temporal.json` (v2) e `_use_labels.json`.

**Mudança de prioridade:** a "verificação individual dos 82 spenders" (Limitação 3) está
RESOLVIDA pela camada de identidade — e o resultado da resolução é a correção acima:
62 dos spenders presumidamente drainers eram protocolos legítimos.

## 3. Achados Corrigidos (Fixed Findings)

1. **[MOTOR] Instabilidade Numérica no Quench (Overflow em Float64)** — Severidade: **MÉDIA** (robustez numérica em condições extremas; sem impacto direto em fundos):
   - *Descrição:* O cálculo dos pesos $W = \frac{5000}{1 + e^{\beta \cdot \Delta E_0}}$ gerava warnings de overflow quando $\Delta E_0$ apresentava variações extremas.
   - *Correção:* Aplicada limitação `np.clip(beta * dE0, -700, 700)` e normalização explícita do vetor $P = P / \sum P$.
2. **[MOTOR] Chamada Incorreta do Método no Experimento de Honestidade** — Severidade: **ALTA** (comprometia a validade da prova de equivalência quench/argmin):
   - *Descrição:* `honesty_experiment.py` chamava `eng.classify(x)` (analítico) no loop do quench em vez de `eng.classify_quench(x)`.
   - *Correção:* Atualizada a chamada para `classify_quench(x)`, comprovando equivalência total de 0/1.848 divergências.
3. **[DATASET] Corrupção de Rótulos de Roteadores DEX Legítimos** — Severidade: **ALTA** (falsos positivos sistemáticos enviesando o ground truth do benchmark):
   - *Descrição:* Endereços de roteadores DEX conhecidos (Uniswap V3, 1inch) estavam classificados como `ATTACK` nos JSONs de dados reais.
   - *Correção:* Reclassificados para `BENIGN` em `real_labeled_approves.json` e `approves_window.json`.
4. **[DATASET] Formatação de Seletores & Diagnóstico de Drainers** — Severidade: **CRÍTICA** (drainers reais eram classificados como ALERTAR em vez de BLOQUEAR — falha de detecção de ataque em produção):
   - *Descrição:* Incompatibilidade na formatação de seletores sem prefixo '0x' fazia com que seletores de aprovação de drainer (`0x23b872dd`) fossem interpretados erroneamente como `ALERTAR` em vez de `BLOQUEAR`.
   - *Correção:* Normalizada a extração e classificação de seletores em `realdata_benchmark.py`, atingindo 10/14 bloqueios diretos e 4/14 alertas (100% recall).
5. **[DEMO] Hexadecimal Incorreto do Chain ID da Arbitrum Sepolia** — Severidade: **BAIXA** (ambiente de demonstração isolado; sem efeito sobre contrato ou extensão em produção):
   - *Descrição:* `demo/wallet.html` continha o valor hexadecimal `0x66eeb` em vez de `0x66eee` (421614 em decimal).
   - *Correção:* Corrigido o valor no arquivo `demo/wallet.html`.
6. **[DOCS/CI] Alinhamento do Tamanho WASM e Metadados do Contrato** — Severidade: **BAIXA** (consistência documental e de CI):
   - *Descrição:* Inconsistências de documentação que citavam a versão v2 do contrato e tamanhos de WASM desatualizados.
   - *Correção:* Atualizados todos os documentos para o contrato v4 (`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`), WASM 23,4 KiB (23.939 bytes).

---


7. **[MOTOR] Aceitação Silenciosa de Features com NaN/Inf (Achado do Fuzz Harness)** — Severidade: **MÉDIA** (entrada inválida produzia veredito NaN sem erro explícito, violando o princípio de falha perceptível):
   - *Descrição:* O fuzz harness (`engine/fuzz_engine.py`, 40.054 entradas adversariais) detectou que `classify()` aceitava vetores contendo NaN, propagando NaN silenciosamente até o veredito.
   - *Correção:* Nova função `validate_features()` recusa explicitamente NaN/Inf com `ValueError` tipado e valida `shape == (8,)` em ambos os caminhos (`classify` e `classify_quench`).
8. **[MOTOR] Overflow de Custos sob Magnitude Extrema (≥ ~1e154)** — Severidade: **MÉDIA** (NaN em probabilidades com inputs de magnitude 1e300; não explorável no pipeline atual, cujas features vivem em [0,1], mas violava a invariante de finitude INV6):
   - *Descrição:* Custos $E = \sum (x - p)^2$ com componentes de magnitude 1e300 saturavam float64 para Inf, produzindo `p_star` NaN e quebrando determinismo (INV5).
   - *Correção:* `validate_features()` projeta o vetor no dominio documentado das features $[0,1]^8$ via `np.clip`, garantindo custos finitos sob qualquer magnitude. Fuzz re-executado: **0 falhas em 40.054 entradas** (recibo em `evidence/fuzz_engine_receipt.json`).

## 4. Limitações Residuais Documentadas

1. **Aplicações sem Provedor EIP-1193/6963 (Navegador):**
   - DApps que operam com carteiras locais via chave privada em código, scripts RPC diretos ou WebSockets sem passar por `window.ethereum` não são interceptados pela extensão do navegador.
2. **Modo FAIL_OPEN durante Indisponibilidade de RPC:**
   - Na configuração padrão (`FAIL_OPEN`), se o nó RPC do ZEUS GUARD na Arbitrum Sepolia/Mainnet ficar offline ou inacessível, a extensão exibe um aviso visual e repassa a transação diretamente para a carteira do usuário. Para segurança estrita, o usuário pode configurar `FAIL_CLOSED`.
3. **Verificação de Identidade — RESOLVIDA em 28/09/2026 (v4.5), com correção de ground truth:** a verificação individual via Blockscout (`engine/label_resolver.py`) revelou que 62 dos spenders presumidamente drainers eram protocolos legítimos verificados. O ground truth foi corrigido por exclusão (473 eventos contaminados): ataques verdadeiros = 54, recall mantido em 100%, FP reduzido a 12,6% com a camada de identidade ativa (seção 2.6). Limitação REMANESCENTE: o cache de labels é um snapshot de 28/09/2026; contratos verificados posteriormente exigem re-resolução periódica em produção.
4. **Truncamento de Janela Temporal no Benchmark Real (Window Right-Censoring):**
   - O dataset real monitora desfechos on-chain até 7.200 blocos (~30 minutos na Arbitrum). Ataques que efetuam a drenagem após esse intervalo temporal são truncados no benchmark.
5. **Frequência Acumulada de Features em Escala de Amostragem:**
   - A métrica de frequência de aprovação por token utiliza uma janela móvel acumulada de ~60k blocos (~1,5 dias).

---

## 5. Evidências de Testes & Execução Reproduzível

Todas as suítes de testes foram executadas e validadas com sucesso:

| Suíte de Testes | Comando | Resultado |
| :--- | :--- | :--- |
| **Rust Unit Tests** | `cd zeus-guard-contract && cargo test` | **15/15 PASS** |
| **Stylus Check & WASM** | `cd zeus-guard-contract && cargo stylus check` | **23.4 KiB PASS** |
| **Invariantes do Motor** | `python3 engine/test_engine_invariants.py` | **5/5 PASS** |
| **Benchmark Sintético QCSN**| `python3 engine/demo.py` | **40/40 PASS** (<0.1 ms/tx) |
| **Experimento de Honestidade**| `python3 engine/honesty_experiment.py` | **0/1848 Divergências** |
| **Benchmark de Dados Reais**| `python3 engine/realdata_benchmark.py` | **100% Recall (14/14), 11.9% FP** |
| **Fuzz Harness Adversarial** | `python3 engine/fuzz_engine.py` | **40.054 entradas / 0 falhas PASS** (INV1..INV7) |
| **Benchmark Real Escalado v2** | `python3 engine/realdata_benchmark_v2.py` | **15.291 eventos, recall 100% (IC95 [99,3%,100%]), FP 14,4%** |
| **Extensão Browser MV3** | `node ext/test_extension.js` | **10/10 PASS** |
| **Smoke Tests On-Chain v4** | `python3 proof/smoke_v4.py` | **13/13 PASS** |
| **Ataque e Defesa ao Vivo** | `python3 proof/live_attack_defense.py` | **4/4 PASS** |

---

## 6. Três Pilares: Defesa Interna, Auditoria Externa e Gates de Mainnet

```
+-----------------------------------------------------------------------------------+
|                                  ZEUS GUARD v4                                    |
+------------------------------------------+----------------------------------------+
|                                          |                                        |
|  [X] PILAR 1: DEFESA INTERNA CONCLUÍDA   |  [ ] PILAR 2: AUDITORIA EXTERNA       |
|  - Contrato Stylus v4 (15/15 testes)     |  - Engajamento de empresa terceirizada |
|  - Motor QCSN & Dataset Real (100% recall|  - Revisão formal Stylus/WASM         |
|  - Extensão MV3 Hook EIP-1193 (10/10)    |  - Remediação de achados externos      |
|  - CI, Invariantes e Smoke v4 (13/13)    |                                        |
+------------------------------------------+----------------------------------------+
|                                                                                   |
|  [ ] PILAR 3: GATES DE DEPLOY EM MAINNET (PENDENTES)                              |
|  - Certificação final de auditoria sem pendências                                 |
|  - Configuração de Multisig e Timelock para Owner/Guardian                        |
|  - Infraestrutura RPC redundante de alta disponibilidade                          |
|  - Script de deploy e verificação pública no Arbiscan Mainnet                      |
+-----------------------------------------------------------------------------------+
```

### Pilar 1: Defesa Interna Concluída [CONCLUÍDO]
- Toda a validação adversarial interna do contrato, motor QCSN, dataset real, extensão MV3 e documentação/CI foi executada com 100% de sucesso.
- Todos os testes unitários, de invariantes, de integração e smoke tests on-chain passaram.

### Pilar 2: Auditoria Externa Pendente [PENDENTE]
- **Submissão Formal:** O pacote `audit-ready` está pronto para envio a auditoras externas (ex: Trail of Bits, OpenZeppelin, Consensys Diligence, Halborn).
- **Escopo do Exame:** Smart contract Rust/Stylus v4, invariantes de cofre e teto diário, intercepção EIP-1193 e algoritmo QCSN.
- **Remediação:** Quaisquer apontamentos decorrentes da auditoria externa deverão ser corrigidos antes de qualquer liberação em produção.

### Pilar 3: Gates de Deploy em Mainnet [BLOQUEADO]
- **Sem Deploy Prematuro:** Nenhum deploy foi realizado na Arbitrum One Mainnet nesta rodada adversarial.
- **Sem Chaves de Produção:** Nenhuma chave privada de produção foi gerada ou armazenada.
- **Pré-requisitos Obrigatórios para Mainnet:**
  1. Relatório assinado e sem vulnerabilidades em aberto emitido por auditora externa reconhecida.
  2. Implementação de carteira multisig (ex: Safe) com Timelock para gerenciar os papéis de `owner` e `guardian`.
  3. Contratação e configuração de endpoints RPC de alta redundância para sustentar a validação em tempo real da extensão e do contrato.
  4. Execução do procedimento de deploy na Arbitrum Mainnet com verificação e publicação do código-fonte e ABI.
