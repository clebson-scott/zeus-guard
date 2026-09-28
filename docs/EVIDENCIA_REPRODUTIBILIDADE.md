# 📊 Pacote de Evidências & Auditoria de Reprodutibilidade — ZEUS GUARD v4

Este documento detalha o pacote de evidências, rigor de reprodutibilidade, fixtures e verificação automatizada do **ZEUS GUARD v4**.

---

## ⚡ Verificação Rápida em 1 Comando (~25 segundos)

Para auditores e juízes re-executarem e auditarem **todas** as 23 verificações de reprodutibilidade do projeto:

```bash
python3 verify_reproducibility.py
```

O script `verify_reproducibility.py` executa o checklist completo de avaliação e **falha com código de saída 1 (sys.exit(1))** se qualquer métrica, fixture, build ou teste divergirem das evidências publicadas.

---

## 📁 Estrutura do Pacote de Evidências (`evidence/`)

O diretório `evidence/` armazena os manifestos e recibos estruturados de execução:

| Arquivo de Evidência | Conteúdo / Verificação Mapeada |
|---|---|
| `evidence/evidence_manifest.json` | Manifesto canônico com metadados do deploy, versão, hashes on-chain e métricas de benchmark |
| `evidence/cargo_test_receipt.txt` | Recibo de execução dos 15 testes unitários do contrato em Rust |
| `evidence/realdata_benchmark.json` | Recibo do benchmark em 81 eventos reais rotulados da Arbitrum Mainnet |
| `evidence/honesty_experiment.json` | Recibo do teste de equivalência quântica-analítica em 1.848 casos (0 divergências) |
| `evidence/extension_test_receipt.txt` | Recibo dos 10 testes do harness da extensão MV3 em JavaScript |
| `evidence/smoke_v4_receipt.json` | Recibo dos 13 testes de integração smoke on-chain na Arbitrum Sepolia |
| `evidence/live_attack_defense_receipt.json` | Recibo dos 4 testes de prova de ataque e defesa ao vivo contra o contrato deployado |

---

## 🔍 Resumo dos Resultados Auditados

### 1. Requisitos & Ferramental
- **Python:** Dependencies declaradas e validadas em `requirements.txt` (`numpy`, `scipy`, `pycryptodome`, `pillow`, `web3`, `eth-utils`).
- **Rust / Stylus:** Rust 1.98.1, `wasm32-unknown-unknown`, `stylus-sdk 0.10.9`.
- **Node.js:** v20+ para os testes do harness EIP-1193 da extensão.

### 2. Ausência de Segredos Privados
- Varredura automatizada confirma **zero** tokens privados de produção, chaves privadas mainnet, credenciais AWS/Infura/Alchemy em código-fonte ou documentação.
- Testes on-chain usam RPC pública (`https://sepolia-rollup.arbitrum.io/rpc`) e consultas em modo leitura sem chave.

### 3. Fixtures & Dados Reais
- `engine/data/real_labeled_approves.json`: 81 eventos reais de approvals na Arbitrum Mainnet, rotulados por desfecho no explorer/chain (14 ataques / 67 benignos).
- `zeus-guard-contract/zeus-guard-abi.json`: ABI canônica exportada pelo Stylus.

### 4. Métricas e Benchmarks
- **Recall em Ataques Reais:** 100.0% (14/14 ataques capturados - 10 bloqueados diretamente, 4 com alerta preventivo).
- **Taxa de Falsos Alarmes (FP):** 11.9% (8/67).
- **Acurácia Global:** 90.1% (73/81).
- **Acurácia do Benchmark Sintético:** 100.0% (40/40 arquetipos, <0.1 ms/tx no caminho analítico argmin).
- **Equivalência Quântica:** 0 divergências entre o quenching dissipativo e o argmin analítico em 1.848 casos testados.

### 5. Contrato On-Chain & Links no Explorer
- **Contrato Canônico v4:** [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a)
- **Tamanho do Artefato WASM:** 23.4 KiB (23.939 bytes) (abaixo do limite de 24 KiB da Stylus).
- **Tx de Deploy:** [`0xe87a27c6da339fa0258f3c8e0213fa71c97146cff18ee9a0e420a1fc467516a3`](https://sepolia.arbiscan.io/tx/0xe87a27c6da339fa0258f3c8e0213fa71c97146cff18ee9a0e420a1fc467516a3)
- **Tx de Ativação Stylus:** [`0x878bf81b6100851f5789603b7ca795fae1a58d42542d79bdaf824d472c15a4d0`](https://sepolia.arbiscan.io/tx/0x878bf81b6100851f5789603b7ca795fae1a58d42542d79bdaf824d472c15a4d0)

---

## 🛠 Suítes de Teste e Comandos de Execução Direta

| Suíte | Comando | Passou / Total |
|---|---|---|
| Contrato em Rust | `cargo test` | 15 / 15 |
| Invariantes do Motor | `python3 -m unittest discover -s engine -p "test_*.py"` | 5 / 5 |
| Harness da Extensão | `node ext/test_extension.js` | 10 / 10 |
| Benchmark Sintético | `python3 engine/demo.py` | 40 / 40 |
| Benchmark Dados Reais | `python3 engine/realdata_benchmark.py` | 14/14 Recall (100%) |
| Experimento de Honestidade | `python3 engine/honesty_experiment.py` | 0 divergências / 1848 |
| Smoke Tests On-Chain | `python3 proof/smoke_v4.py` | 13 / 13 |
| Prova Ataque/Defesa Vivo | `python3 proof/live_attack_defense.py --rpc ... --contract ...` | 4 / 4 |
