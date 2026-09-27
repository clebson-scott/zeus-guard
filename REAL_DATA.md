# 📊 Dados Reais — Metodologia, Benchmark e Resultados (v4 Release)

Este documento detalha a metodologia de amostragem, rotulagem neutra por desfecho on-chain e os resultados do benchmark do **ZEUS GUARD QCSN Risk Engine** sobre dados reais da **Arbitrum Mainnet**.

---

## 1. Metodologia de Coleta e Rotulagem (Sem Vazamento Temporal)

1. **Coleta de Eventos (`engine/data/collect_approves.py`)**:
   - Amostragem de 60.000 blocos da Arbitrum mainnet (RPC pública).
   - Extração dos eventos `Approve(owner, spender, value)` armazenados em `engine/data/approves_window.json`.

2. **Rotulagem por Desfecho On-Chain (`engine/data/label_by_outcome.py`)**:
   - **`ATTACK`**: Approve ilimitado direcionado a EOA ou contrato não verificado que resultou em drenagem (`transferFrom` por terceiro) em até 4h pós-approve.
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
ataques capturados (recall):    14/14 = 100.0%
falsos alarmes (FP rate):       8/67 = 11.9%
acuracia global:                90.1%
------------------------------------------------------------------
baseline 'ilimitado ou EOA':    recall 100.0% | FP 89.6%

Labels de ground truth (desfecho, sem vazamento temporal):
  ATTACK                 = approve ilimitado em EOA/unverified seguido de pull por terceiro em <= 4h
  BENIGN                 = sem pull de ataque na janela (inclui DEX/routers legitimos)
  pulled_by_third_party  = contagem bruta de transacoes com transferFrom por terceiro
```

---

## 3. Comparativo de Desempenho

| Métrica | Baseline Heurístico ("Ilimitado ou EOA") | Motor ZEUS GUARD QCSN | Melhoria |
|---|---|---|---|
| **Recall de Ataques (Drainers)** | 100.0% (14/14) | **100.0% (14/14)** | Cobertura total mantida |
| **Taxa de Falsos Alarmes (FP Rate)** | 89.6% (60/67) | **11.9% (8/67)** | **Redução de 77.7 p.p. em alarmes falsos** |
| **Acurácia Global** | 22.2% (18/81) | **90.1% (73/81)** | **Ganho drástico na precisão operacional** |

---

## 4. Limitações Declaradas

- **Janela Observacional de 4h:** Ataques onde a drenagem ocorre após mais de 4 horas da aprovação são classificados como benignos no ground truth atual.
- **Vetor `destino_envenenado`:** Heurística de address poisoning mantida em 0 no benchmark de aprovações isoladas (requer histórico de transferências de poeira).
- **Taxa de Falsos Positivos de 11,9%:** Aprovações de valor elevado em contratos novos/não verificados ainda geram alertas preventivos (comportamento seguro por padrão).
