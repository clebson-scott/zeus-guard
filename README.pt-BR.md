# ⚡ ZEUS GUARD — O Guardião de Traders da Robinhood Chain

> O antivírus on-chain do trader pessoa-física: firewall pré-transação, revogação
> automática de approvals perigosos, cofre USDG com janela de desafio e escudo de
> liquidação — movido por um motor de seleção dissipativa de risco validado em
> hardware quântico real (IBM Quantum, `ibm_fez`).

**Autor:** Clebson Campos de Araujo · Arbitrum Open House Singapore 2026 · Buildathon

---

## 🎯 O problema

A Robinhood Chain vai trazer **milhões de usuários leigos** on-chain. Leigos perdem
**bilhões de dólares por ano** para: approvals envenenados (drainers), address
poisoning, e liquidações evitáveis. Nenhuma carteira do ecossistema tem um guardião.

## 🛡️ O produto

| Módulo | Função |
|---|---|
| **Firewall pré-transação** | Toda tx passa pelo agente; simulação + análise de calldata bloqueia scam antes de assinar |
| **Auto-revogação** | Approvals com risco alto são revogados pelo guardião sem ação do usuário |
| **Cofre USDG** (bônus Paxos!) | Pagamentos ficam retidos numa janela de desafio — drainer não move valor no mesmo bloco |
| **Disjuntor de emergência** | Ataque em andamento congela a sessão inteira |
| **Telemetria pública** | Cada veredito emite eventos auditáveis on-chain — dashboard Dune no roadmap |

## ⚛️ O diferencial técnico: motor QCSN de risco

O classificador de risco usa **seleção dissipativa de ramos (quench de Gibbs, β 2→40)**
sobre uma paisagem de arquétipos de ataque — o mesmo mecanismo que medimos em
processador quântico real da IBM (job `daorvfg2fm4c73f5tlog`, backend `ibm_fez`,
fidelidade de seleção 0,997) e integramos por exponencial de matriz exata.

**Benchmark (dataset sintético de 40 txs, 5 arquétipos):**
- Motor QCSN: **100% de acurácia**, confiança média p* ≈ 0,99, **0,9 ms/tx**
- Limiar fixo (baseline): 95%
- Latência de transação real: o quench completo de 60 passos cabe no bloqueio

*Nota honesta: dataset sintético com arquétipos separáveis; dados reais serão
mais ruidosos. A validação mostra que o mecanismo roda em velocidade de tx.*

## 🦀 O contrato (Stylus / Rust)

`contracts/zeus_guard.rs` — sessões de guardião, registro de approvals com score
de risco, revogação, cofre USDG com janela de desafio, disjunção de emergência.
*Draft de referência para stylus-sdk; adaptar à versão exata durante
`cargo stylus check` (ver docs.arbitrum.io/stylus/quickstart).*

Build & deploy (após instalar Rust + cargo-stylus):
```bash
cargo stylus check --endpoint https://sepolia.arbitrum.io  # ou RPC da Robinhood Chain testnet
cargo stylus deploy --endpoint <RPC> --private-key <KEY>
```
Faucets: `faucet.testnet.chain.robinhood.com` (Robinhood) · `faucet.circle.com` (USDC/USDG test)

## 📊 Matriz de julgamento

| Critério | ZEUS GUARD |
|---|---|
| Qualidade de contrato | Rust/Stylus + patterns limpos, erros tipados, eventos auditáveis |
| Product-Market Fit | Todo retail trader da maior corretora onboarding do mundo |
| Inovação | Primeiro guardião com política em Rust + motor dissipativo |
| Problema real | Perdas por scam: bilhões/ano |
| Bônus USDG (Paxos) | ✓ Cofre nativo |
| Slot reservado Robinhood Chain | ✓ Deploy na testnet deles |

## 📁 Estrutura

```
zeus_guard/
├── contracts/zeus_guard.rs     # contrato Stylus (Rust)
├── engine/qcsn_risk_engine.py # motor dissipativo de risco
├── engine/demo.py              # benchmark: 40/40, 1.1 ms/tx
└── docs/SUBMISSAO_CHECKLIST.md # roteiro de 10 dias ate 04/out
```

> "A maioria das pessoas olha para uma profissão e vê um teto. Eu olho para todas
> ao mesmo tempo e vejo uma ponte." — e esta ponte guarda teu dinheiro.

## 🚀 DEPLOY OFICIAL (Arbitrum Sepolia)
- **Contrato v2 (atual):** `0x038409e301e32467b226d10c728a0c6fbe28ea4a` — Explorer: https://sepolia.arbiscan.io/address/0x038409e301e32467b226d10c728a0c6fbe28ea4a
- Ativação Stylus v2: tx `0x2e658e8abb37549d42671da8970bc3b06f053c2c83bc2d03ed72c00033f51978`
- Smoke tests v2 (26/09/2026): bloqueia drainer (TooRisky), bloqueia acima do teto (AboveDailyCap), libera tx normal, exige sessão (NoSession), blinda janela de desafio (ChallengeWindowOpen)
- v1 (histórico): `0x313e9994f1e77f579e797c19e29250a9a782e3a5` — receipts em `deploy/DEPLOYADO_ARBITRUM_SEPOLIA.md`
