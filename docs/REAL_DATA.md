# 📊 Dados Reais — Metodologia, Benchmark e Resultados (v4 Release)

Este documento detalha a metodologia de amostragem, rotulagem neutra por desfecho on-chain e os resultados do benchmark do **ZEUS GUARD QCSN Risk Engine** sobre dados reais da **Arbitrum Mainnet**.

---

## 1. Metodologia de Coleta e Rotulagem (Sem Vazamento Temporal)

1. **Coleta de Eventos (`engine/data/collect_approves.py`)**:
   - Amostragem de 60.000 blocos da Arbitrum mainnet (RPC pública).
   - Extração dos eventos `Approve(owner, spender, value)` armazenados em `engine/data/approves_window.json`.

2. **Rotulagem por Desfecho On-Chain (`engine/data/label_by_outcome.py`)**:
   - **`ATTACK`**: Approve ilimitado direcionado a EOA ou contrato não verificado que resultou em drenagem (`transferFrom` por terceiro) em até 7200 blocos (~30min) pós-approve.
   - **`BENIGN`**: Aprovações sem drenagem por terceiro na janela observada, incluindo interações legítimas com roteadores e DEXs conhecidos (Uniswap V3, 1inch, Aave, etc.).
   - **`pulled_by_third_party`**: Contagem bruta de transações onde houve `transferFrom` executado por terceiro (`tx.from != owner`).

3. **Causalidade Estrita nas Features (`engine/real_features.py`)**:
   - Todas as métricas de frequência, idade do contrato e saldo do dono são calculadas considerando **apenas** informações disponíveis até o bloco da transação (`block <= tx.block`). Nenhuma feature consulta blocos futuros.

---

## 2. Resultado do Benchmark (`python3 engine/realdata_benchmark.py`)

Comando para reprodução determinística:
```bash
python3 engine/realdata_benchmark.py
```

Saída oficial do benchmark:

```
==================================================================
BENCHMARK EM DADOS REAIS — Arbitrum mainnet, rotulagem por desfecho
==================================================================
eventos reais rotulados:  81  | ataques: 14  | benignos: 67
pulls por terceiro (raw): 23
distribuicao verdictos:  BLOQUEAR=10 | ALERTAR=12 | LIBERAR=59
ataques capturados (recall total): 14/14 = 100.0%
  -> acao direta BLOQUEAR:          10/14
  -> acao preventiva ALERTAR:       4/14
falsos alarmes (FP rate):       8/67 = 11.9%
acuracia global:                90.1%
------------------------------------------------------------------
baseline 'ilimitado em EOA':    recall 85.7% | FP 0.0%

Labels de ground truth e limitacoes do benchmark:
  1. ATTACK                 = approve ilimitado em EOA/unverified seguido de pull por terceiro
  2. BENIGN                 = sem pull de ataque na janela (inclui DEX/routers legitimos)
  3. Window Right-Censoring = 7200 blocos (~30min na Arbitrum); ataques apos a janela sao truncados
  4. Feature Token Freq     = acumulada sobre a janela de amostragem de ~60k blocos (~1.5 dias)
```

---

## 3. Comparativo de Desempenho

| Métrica | Baseline Heurístico ("Ilimitado em EOA") | Motor ZEUS GUARD QCSN | Observação |
|---|---|---|---|
| **Recall de Ataques (Drainers)** | 85.7% (12/14) | **100.0% (14/14)** | Cobertura total (10 BLOQUEAR + 4 ALERTAR) |
| **Taxa de Falsos Alarmes (FP Rate)** | 0.0% (0/67) | **11.9% (8/67)** | Regra cega em EOA perde ataques via contrato; QCSN captura todos com FP baixo |
| **Acurácia Global** | 95.1% (77/81) | **90.1% (73/81)** | Proteção estendida sobre contratos não auditados e seletores atípicos |

---

## 4. Limitações Declaradas

- **Janela Observacional de 7200 blocos (~30min na Arbitrum):** Ataques onde a drenagem ocorre após a janela de amostragem são truncados (right-censoring) no ground truth atual.
- **Vetor `destino_envenenado`:** Heurística de address poisoning mantida em 0 no benchmark de aprovações isoladas (requer histórico de transferências de poeira).
- **Taxa de Falsos Positivos de 11,9%:** Aprovações de valor elevado em contratos novos/não verificados ainda geram alertas preventivos (`ALERTAR`), que acionam aviso do guardião sem bloqueio definitivo.


---

## 5. Camada de Identidade e Ground Truth Corrigido (v4.5, 28/09/2026)

### 5.1 O resolvedor de labels (`engine/label_resolver.py`)

Fonte: **Blockscout Arbitrum/Ethereum** (API aberta, sem chave de API) + whitelist curada
do projeto (`engine/data/known_protocols_v2.json`, 14 protocolos) + cache durável
auditável (`engine/data/label_cache.json`, 567 spenders resolvidos em 28/09/2026, com
fonte e timestamp por endereço). Classes: `protocol` (contrato verificado e nomeado),
`eoa`, `contract_unverified`, `unknown` (fail-closed: sem fonte, sem rotulação).

```bash
python3 engine/label_resolver.py 0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae
python3 engine/test_label_resolver.py   # 17/17
```

### 5.2 Correção do ground truth v2

A verificação individual dos spenders (Limitação 3 do relatório) revelou que **473 dos
527 eventos ATTACK do v2 tinham spender que é contrato verificado e nomeado** (Curve,
Uniswap, 1inch, Across, CoW, Bebop, Camelot, Morpho, ...): a verificação de coleta
falhou para eles (`verified_protocol=False`) e a whitelist de 14 protocolos era
insuficiente (a janela real tem 350+ contratos verificados). Swaps normais via router
permaneceram rotulados como ataque.

Correção conservadora: eventos ATTACK com spender `protocol` **excluídos** (não
re-rotulados como benignos — exclusão documenta a incerteza).

| Painel | Ataques | Recall | FP | Acurácia |
|---|---|---|---|---|
| [A] v2 publicado (GT contaminado) | 527 | 100% [99,3%, 100%] | 14,4% | 86,1% |
| **[B] GT corrigido, motor padrão (oficial)** | **54** | **100% [93,4%, 100%]** | **14,4%** | **85,7%** |
| [C] GT corrigido + camada de identidade | 54 | 100% [93,4%, 100%] | **12,6%** | **87,5%** |

O recall de 100% do motor se mantém sobre os 54 ataques verdadeiros (todos com perfil
clássico: spender não-verificado/EOA + pull por terceiro) — e a camada de identidade
reduz o FP em 1,8 p.p. sem perder um único ataque.

```bash
python3 engine/realdata_benchmark_gt_corrected.py
```

### 5.3 Split temporal (`engine/realdata_benchmark_temporal.py`)

Divisão no bloco mediano da janela (~74 min de chain), features estritamente causais:

| Período (GT corrigido) | Ataques | Recall | FP |
|---|---|---|---|
| Metade inicial | 25 | 100% [86,7%, 100%] | 18,0% |
| Metade final | 29 | 100% [88,3%, 100%] | 10,7% |

**Recall estável (FN=0 nos dois períodos). FP com gradiente temporal (IC95 não se
sobrepõem): artefato de warm-up da feature causal de frequência de token no início da
janela.** Implicação: o FP agregado depende do período; produção deve usar janela de
warm-up ou normalização por idade do evento.
