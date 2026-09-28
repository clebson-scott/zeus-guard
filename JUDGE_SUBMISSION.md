# 🛡️ ZEUS GUARD v4 — JUDGE SUBMISSION PACKAGE & COMPETITION DOSSIER

> **Status do Pacote**: AUDIT-READY & FULLY REPRODUCIBLE
> **Rede**: Arbitrum Sepolia (Chain ID: 421614 / `0x66eee`)
> **Contrato Stylus v4**: `0xa9ef4e9be0e8f45e737f361380743faab72fe76a`
> **Executável de Reprodutibilidade (1 Comando)**: `python3 verify_reproducibility.py` (23/23 verificações aprovadas)

---

## ⚡ 1. PITCH DE 60 SEGUNDOS (ELEVATOR PITCH)

A maioria dos ataques Web3 em carteiras de usuários — como drenadores EIP-712 e approvals maliciosos — falha na prevenção porque as defesas atuais atuam *após* o usuário ter assinado a transação ou tentam simular transações no RPC quando já é tarde demais.

O **ZEUS GUARD v4** é um sistema de defesa ativa em duas camadas independentes que bloqueia ataques **antes** que a carteira abra a janela de assinatura:

1. **Camada Pré-Carteira (Hook EIP-1193)**: Intercepta requisições `eth_sendTransaction` e `eth_signTypedData_v4` em `document_start`. Antes mesmo de abrir a MetaMask ou Rabby, o motor consulta o score de risco off-chain e o estado de revogação on-chain (`approvalStatusPub`). Se for um drenador ou permit revogado, a requisição é abortada com código EIP-1193 `4001` (User Rejected Request). **Zero assinatura gerada, zero chave exposta.**

2. **Cofre On-Chain Imutável em Rust / Stylus WASM**: Caso uma transação chegue à blockchain, o contrato imutável Stylus v4 (`0xa9ef...76a`, apenas 23.4 KiB WASM) atua como firewall determinístico. Ele impõe teto de risco (Score ≥ 60%), limite diário rolante de 24 horas, janela de contestação de custódia (≥120s para pagamentos USDG) e congelamento de sessão de emergência por um guardião.

3. **Motor de Risco QCSN Sem Quantum Washing**: O motor analítico é derivado de física de Redes de Spins Contínuos Quânticas (QCSN), validado no QPU `ibm_fez` da IBM (fidelidade 0.997). Em produção, roda o argmin analítico determinístico em **<0.1 ms por transação**, com **100.0% de recall em 14 ataques reais da Arbitrum Mainnet** e **0 divergências em 1.848 testes** com a integração quântica.

---

## 🎬 2. ROTEIRO DE DEMONSTRAÇÃO PARA JUIZES (DEMO SCRIPT)

Existem **duas formas** de testar e reproduzir o núcleo da demonstração: um runner mestre automatizado via CLI em 1 linha e uma interface web interativa sem necessidade de conectar carteira real.

### Opção A: Execução em 1 Comando via CLI (~30 segundos)

Abra o terminal na raiz do repositório `/tmp/zeus-guard` e execute:

```bash
python3 proof/demo_judges.py
```

**O que este script executa ao vivo:**
1. **Benchmark QCSN Off-Chain**: Avalia 40 arquétipos de transação sintética em <0.1 ms/tx, mostrando acurácia de 100%.
2. **Verificação On-Chain ao Vivo (Arbitrum Sepolia)**: Chama `checkTx` diretamente no contrato Stylus v4 (`0xa9ef...76a`):
   - **Cenário 1 (Legítimo - Café 25 USDG)**: Risco 2% (250 bps) → Retorna Sucesso On-Chain.
   - **Cenário 2 (Ataque Bloqueado - Fake Airdrop)**: Risco 97% (9700 bps) → Reverte On-Chain com erro imutável `TooRisky(9700, 6000)`.
3. **Consulta de Revogação Pré-Carteira**: Consulta `approvalStatusPub` para o endereço de drenador revogado (`0x0000...dEaD`) e roda a suíte de testes do Hook EIP-1193 (10/10 PASS) confirmando rejeição `4001` antes da carteira.
4. **Verificação de Registros**: Confirma o estado ao vivo da sessão e exibe links no Arbiscan.

---

### Opção B: Interface Web Interativa (`demo/wallet.html`) (~2 minutos)

1. Abra o arquivo `demo/wallet.html` no seu navegador (ex: `google-chrome demo/wallet.html` ou simplesmente dando duplo clique no arquivo).
2. A interface utiliza o **DEMO USER** v4 com sessão ativa na Arbitrum Sepolia (`0x1718bd9000B81bD5996DeE981eb76232bc2438B3`).
3. Siga o roteiro em 4 Passos na tela:
   - **Passo 1 (Legítimo)**: Clique em `[1] Executar Café/Swap 25 USDG`. Resultado: O motor calcula Score 2% e o RPC da Arbitrum Sepolia confirma aprovação on-chain.
   - **Passo 2 (Ataque Drenador)**: Clique em `[2] Tentativa Claim Airdrop Falso`. Resultado: O motor calcula Score 97% e o contrato Stylus reverte com `TooRisky`.
   - **Passo 3 (Intercepção Pré-Carteira)**: Clique em `[3] Tentar Assinar Permit Revogado`. Resultado: O hook EIP-1193 lê `approvalStatusPub` (revoked=true) e simula o cancelamento do prompt da carteira (Erro 4001) **sem abrir a janela da MetaMask**.
   - **Passo 4 (Evidência On-Chain)**: Clique em `[4] Verificar Estado On-Chain` para ler a sessão e os links diretos do Arbiscan Sepolia.

---

## 📊 3. MÉTRICAS VERIFICADAS E RESULTADOS AUDITADOS

Todas as métricas abaixo foram geradas e verificadas pela suíte automatizada `verify_reproducibility.py` e registradas em `evidence/evidence_manifest.json`:

| Categoria | Métrica Verificada | Valor Obtido | Status / Evidência |
|---|---|---|---|
| **Benchmark de Dados Reais** | Total de eventos reais analisados (Arbitrum Mainnet) | **81 eventos** | `engine/data/real_labeled_approves.json` |
| | **Recall em Drenadores/Ataques** | **100.0% (14/14)** | Zero drenadores não detectados |
| | Taxa de Falsos Positivos (FP Rate) | **11.9% (8/67)** | Queda expressiva vs 89.6% do baseline ingênuo |
| | Acurácia Global em Dados Reais | **90.1%** | `evidence/realdata_benchmark.json` |
| **Experimento de Honestidade** | Divergências entre Quench Quântico e Argmin Analítico | **0 divergências (em 1.848 testes)** | `evidence/honesty_experiment.json` |
| **Desempenho Off-Chain** | Latência média do motor de risco QCSN | **< 0.1 ms / tx** | Custo insignificante na experiência do usuário |
| **Contrato Stylus v4** | Tamanho do binário WASM compilado em Rust | **23.4 KiB (23.939 bytes)** | Limite Stylus: 24.0 KiB |
| | Testes Unitários do Contrato em Rust | **15/15 PASS** | `cargo test` |
| | Testes do Hook Extension MV3 (Node.js) | **10/10 PASS** | `ext/test_extension.js` |
| | Testes de Invariante do Motor (Python) | **5/5 PASS** | `engine/test_engine_invariants.py` |
| | Testes Smoke On-Chain v4 (Arbitrum Sepolia) | **13/13 PASS** | `proof/smoke_v4.py` |
| | Prova de Ataque e Defesa Ao Vivo | **4/4 PASS** | `proof/live_attack_defense.py` |

---

## 🔗 4. LINKS E EVIDÊNCIAS ON-CHAIN

- **Rede**: Arbitrum Sepolia Testnet (Chain ID: `421614` / `0x66eee`)
- **RPC Público**: `https://sepolia-rollup.arbitrum.io/rpc`
- **Endereço do Contrato ZEUS GUARD v4**: [`0xa9ef4e9be0e8f45e737f361380743faab72fe76a`](https://sepolia.arbiscan.io/address/0xa9ef4e9be0e8f45e737f361380743faab72fe76a)
- **Transação de Deploy (Initcode)**: [`0xe87a27c6da339fa0258f3c8e0213fa71c97146cff18ee9a0e420a1fc467516a3`](https://sepolia.arbiscan.io/tx/0xe87a27c6da339fa0258f3c8e0213fa71c97146cff18ee9a0e420a1fc467516a3)
- **Transação de Ativação WASM (Stylus)**: [`0x878bf81b6100851f5789603b7ca795fae1a58d42542d79bdaf824d472c15a4d0`](https://sepolia.arbiscan.io/tx/0x878bf81b6100851f5789603b7ca795fae1a58d42542d79bdaf824d472c15a4d0)
- **Carteira do Guardião & Deployer com Sessão Ativa**: [`0x1718bd9000B81bD5996DeE981eb76232bc2438B3`](https://sepolia.arbiscan.io/address/0x1718bd9000B81bD5996DeE981eb76232bc2438B3)
- **Contrato Mock USDG de Teste**: [`0x96Fa5CeA89e749e30686084A1bE522EC7d12Dab9`](https://sepolia.arbiscan.io/address/0x96Fa5CeA89e749e30686084A1bE522EC7d12Dab9)

---

## 💡 5. DIFERENCIAIS ("POR QUE ISSO É DIFERENTE?")

1. **Defesa Pré-Carteira Verdadeira**: Não dependemos de avisos visuais dentro de extensões que o usuário pode simplesmente ignorar ou fechar por engano. O Hook EIP-1193 rejeita a requisição no canal do provedor, cancelando o fluxo antes do prompt de assinatura da chave privada.
2. **Execução On-Chain Imutável em Rust / Stylus**: A lógica de firewall não fica apenas em servidores web vulneráveis. Regras vitais (teto de risco, limites diários, congelamento de sessão, custódia e revogação) são executadas por um contrato Stylus compilado para WASM com a segurança de memória e a performance do Rust.
3. **Honestidade Científica no Uso de Quantum (Sem Quantum Washing)**: Não afirmamos falsamente que o contrato da blockchain roda em um computador quântico. Mapeamos formalmente a dinâmica de dissipação de Redes de Spins Contínuos em hardware quântico real (`ibm_fez`), mas implementamos em produção a solução analítica determinística correspondente (`argmin`), garantindo latência sub-milisegundo (<0.1 ms) e 100% de reproducibilidade lógica (0 divergências comprovadas).
4. **Registro On-Chain de Revogação de Approvals**: O método `approvalStatusPub` mantém um inventário público e auditável de spenders autorizados e revogados, servindo como fonte única de verdade para dApps, agentes e extensões.

---

## ⚠️ 6. LIMITAÇÕES CONHECIDAS

1. **Falsos Positivos em Contratos Recém-Criados (11.9%)**: Contratos legítimos implantados há poucas horas ou sem histórico de transações recebem pontuações de risco ligeiramente mais elevadas devido ao peso dado à maturidade e reputação do contrato no grafo QCSN.
2. **Latência no Cofre de Custódia (≥120s)**: A proteção do cofre USDG exige um período mínimo de desafio (janela de contestação de no mínimo 120 segundos) para autorizar a liberação final de fundos de alto risco, o que impede finalidade instantânea para este tipo específico de liquidação.
3. **Dependência de Fallbacks em RPCs**: Em cenários onde nós RPC públicos da testnet apresentam indisponibilidade ou latência excessiva, o sistema recorre a um modo de fallback seguro que prioriza o bloqueio conservador.

---

## 🛡️ 7. RISCOS RESIDUAIS

1. **Ataques de Engenharia Social Fora da Cadeia**: Se um usuário for induzido a exportar manualmente sua chave privada ou seed phrase diretamente fora de uma carteira Web3 compatível com EIP-1193, a defesa pré-carteira não poderá interceptar o evento.
2. **Padrões Inéditos de Drenadores Zero-Day**: Embora o motor cubra 100% dos 14 tipos de ataques catalogados na Arbitrum Mainnet, vetores de ataque completamente novos que não utilizem approves, permits nem métodos conhecidos exigem constante atualização dos pesos das primitivas do grafo QCSN.
3. **Bypass por Substituição Manual de Provider**: Usuários avançados que intencionalmente desativem a extensão do navegador ou desabilitem o hook EIP-1193 ficam protegidos apenas pela camada on-chain do contrato Stylus.

---

## ✅ 8. CHECKLIST DE APRESENTAÇÃO E REPRODUTIBILIDADE PARA JUIZES

Para auditores e juízes que desejam testar e validar este repositório do zero:

- [x] **Clonar e Instalar**:
  ```bash
  pip install -r requirements.txt
  ```
- [x] **Executar Verificação Completa de Reprodutibilidade**:
  ```bash
  python3 verify_reproducibility.py
  ```
  *(Deve retornar `ALL 23/23 AUDIT CHECKS PASSED PERFECTLY!` em aproximadamente 25 segundos)*

- [x] **Executar Runner da Demonstração Mestre**:
  ```bash
  python3 proof/demo_judges.py
  ```

- [x] **Verificar os Testes do Contrato Stylus em Rust**:
  ```bash
  cd zeus-guard-contract && cargo test && cargo stylus check
  ```

- [x] **Verificar Experimento de Honestidade Quântico-Analítico**:
  ```bash
  python3 engine/honesty_experiment.py
  ```

- [x] **Inspecionar Evidências e Recibos**:
  Verifique o manifesto em `evidence/evidence_manifest.json` e os arquivos de recibo brutos em `evidence/`.

- [x] **Abrir Interface Web Interativa**:
  Abra `demo/wallet.html` no seu navegador de preferência e execute a simulação visual em 4 passos.

---
*ZEUS GUARD v4 — Constrito por Código Imutável e Matemática Verificável.*
