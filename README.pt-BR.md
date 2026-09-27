# ⚡ ZEUS GUARD — Firewall Pré-Transação para Traders Varejo

> O antivírus on-chain do trader pessoa-física: firewall pré-transação com revogação de
> aprovações envenenadas, cofre de custódia USDG com janela de desafio e disjuntor de
> emergência — movido por um **motor de risco rápido e determinístico** (com a validação em
> hardware quântico mantida como pesquisa aberta). Sem matemática misteriosa: o motor de
> produção é um argmin medido e auditável.

**Autor:** Clebson Campos de Araújo (Clebson Scott) · Arbitrum Open House Singapore 2026 · Buildathon
**Repositório:** https://github.com/clebson-scott/zeus-guard · **Landing:** https://telegra.ph/ZEUS-GUARD--Pre-Transaction-Firewall-for-Everyday-Traders-09-26

---

## 🎯 RESUMO — Estado Atual da Release (v4 Release Candidate)

| Componente | Status & Evidências |
|---|---|
| **Contrato Stylus (v4)** | [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a) na Arbitrum Sepolia (Chain ID 421614) · Artefato WASM: 23,4 KiB |
| **Testes Nativos do Contrato** | `cd zeus-guard-contract && cargo test` — **15/15 testes passando** (autorização de cofre, restrição de token, restauração de teto diário 24h, reentrância, imutabilidade sob congelamento, prazo de disputa, erros tipados) |
| **Motor QCSN & Honestidade** | `python3 engine/honesty_experiment.py` — **0 divergências entre quench e argmin em 1.863 casos de teste**; latência analítica **<0,1 ms/tx** |
| **Benchmark em Dados Reais** | `python3 engine/realdata_benchmark.py` — **81 eventos reais da Arbitrum**: **100,0% Recall** (14/14 drainers bloqueados), **11,9% FP Rate** (redução drástica vs 89,6% baseline), **90,1% Acurácia Global** |
| **Extensão MV3 & Hook EIP-1193** | `node ext/test_extension.js` — **7/7 testes passando** (injeção antecipada, validação EIP-712 via `approval_status_pub`, cancelamento com erro EIP-1193 4001, modos `FAIL_OPEN` e `FAIL_CLOSED`) |
| **Smoke Tests On-Chain (v4)** | `python3 proof/smoke_v4.py` — **13/13 passadas na testnet** |
| **Prova de Ataque & Defesa Vivo** | `python3 proof/live_attack_defense.py --rpc ... --contract 0xa9ef... --victim ...` — **4/4 passadas ao vivo** contra o contrato deployado |
| **CI Automatizado** | `.github/workflows/ci.yml` — Integração contínua cobrindo Stylus (15/15), motor de risco e extensão (7/7) |
| **Pacote de Auditoria** | [`docs/AUDIT_CHECKLIST.md`](docs/AUDIT_CHECKLIST.md) · [`SECURITY.md`](SECURITY.md) · [`REAL_DATA.md`](REAL_DATA.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/MATH.md`](docs/MATH.md) |

---

## 🛡️ Arquitetura do Produto

| Módulo | Função | Camada de Execução |
|---|---|---|
| **Firewall Pré-Transação** | Analisa cada transação e permit antes da assinatura; bloqueia drainers (`TooRisky`) e violações de limite (`AboveDailyCap`). | Extensão MV3 (`zeus_hook.js`) & Contrato Stylus (`check_tx`) |
| **Registro de Revogação Pública (`approval_status_pub`)** | Expõe na chain o estado do approval e revogação para leitura por carteiras antes de assinar. | Contrato Stylus v4 & Hook EIP-712 |
| **Cofre de Custódia USDG** | Retém pagamentos via `IERC20.transferFrom` por uma janela de desafio (≥120s). | Contrato Stylus (`escrow_payment` / `vault_send`) |
| **Disputa & Reembolso do Guardião** | Permite contestação pelo guardião e reembolso imediato à vítima (`refund_disputed`) restaurando o limite ativo. | Contrato Stylus (`dispute_payment` / `refund_disputed`) |
| **Disjuntor de Emergência** | Congela a sessão do usuário (`session_frozen`) impedindo qualquer mutação no contrato em caso de ataque. | Contrato Stylus (`freeze_session`) |

---

## ⚛️ O Motor de Risco QCSN: Determinístico e Auditável

O classificador calcula a **seleção por menor distância ao quadrado de arquétipos de ataque (argmin)** com distribuição de probabilidade de Gibbs exata. O processo dissipativo de quench em 60 passos foi testado e provou ser matematicamente idêntico ao argmin em 1.863 casos de teste (`python3 engine/honesty_experiment.py` — 0 divergências). O caminho de produção utiliza o argmin analítico (<0,1 ms/tx).

### Benchmark em Dados Reais (`python3 engine/realdata_benchmark.py`)

- **Dataset:** 81 eventos reais de `Approve` coletados da Arbitrum Mainnet, rotulados estritamente pelo desfecho on-chain sem vazamento temporal (`block <= tx.block`).
- **Ataques Capturados (Recall):** 14/14 (**100,0% Recall**).
- **Taxa de Falsos Positivos:** **11,9%** (8/67 benignos), em comparação com **89,6%** do baseline "approve ilimitado / EOA".
- **Acurácia Global:** **90,1%** (73/81 classificados corretamente).

---

## 🦀 Smart Contract (Stylus / Rust v4)

- **Endereço Deployado:** [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a)
- **Chain ID:** Arbitrum Sepolia (`421614`)
- **Garantias de Segurança Implementadas:**
  - `is_vault_authorized` restringe acesso ao cofre em `vault_send`.
  - `is_token_allowed` limita operações ao token USDG registrado (`session_usdg`).
  - `ReentrancyGuard` protege todas as chamadas de transferência de token.
  - Janela rolante de 24h com restauração segura (`restore_daily_spent`).
  - Sanitização de inputs contra panics (`amount_fits_u128`, `risk_saturating`, `u64_saturating`).

---

## 🚀 Comandos Rápidos de Execução e Verificação

```bash
# 1. Executar Testes Nativos do Contrato (15/15 PASS)
cd zeus-guard-contract && cargo test

# 2. Verificar Compilação WASM Stylus (23,4 KiB)
cargo stylus check

# 3. Executar Benchmark Sintético e Experimento de Honestidade
python3 engine/demo.py
python3 engine/honesty_experiment.py

# 4. Executar Benchmark em Dados Reais (100% Recall, 11,9% FP)
python3 engine/realdata_benchmark.py

# 5. Executar Suíte de Testes da Extensão MV3 (7/7 PASS)
node ext/test_extension.js

# 6. Executar Smoke Tests On-Chain v4
python3 proof/smoke_v4.py

# 7. Executar Prova de Ataque e Defesa Vivo
python3 proof/live_attack_defense.py --rpc https://sepolia-rollup.arbitrum.io/rpc \
  --contract 0xa9ef4e9be0e8f45e737f361380743faab72fe76a \
  --victim 0x1718bd9000B81bD5996DeE981eb76232bc2438B3
```

---

## 🚦 Relatório Final de Prontidão de Release

1. **Pronto Agora na Testnet (Arbitrum Sepolia):**
   - Contrato Stylus v4 ativo em `0xa9ef4e9be0e8f45e737f361380743faab72fe76a`.
   - Todas as suítes de teste passando sem erros (15/15 Rust, 7/7 Node extension, 13/13 smoke on-chain, 4/4 ao vivo).
2. **Pronto para Auditoria Externa:**
   - Pacote completo compilado em `docs/AUDIT_CHECKLIST.md`, `SECURITY.md`, `REAL_DATA.md`, `ARCHITECTURE.md` e `MATH.md`.
3. **Bloqueado para Mainnet:**
   - Publicação em Mainnet **estritamente bloqueada** até a realização de auditoria externa formal por empresa especializada de segurança e configuração de chave/multisig de produção.
