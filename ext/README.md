# 🧩 ZEUS GUARD Extension — Firewall Pré-Assinatura no Navegador (MV3)

Extensão Chrome/Edge/Brave (Manifest V3) que intercepta **todas as transações e assinaturas de permit (EIP-712)** antes de chegarem à carteira:

```
dapp ──> window.ethereum.request(eth_sendTransaction / eth_signTypedData_v4 / personal_sign)
              │
              ▼
        ZEUS GUARD hook          ← 1. Instalação antecipada (trap Object.defineProperty + EIP-6963)
              │                     2. Consulta registro v6 hardened on-chain (approvalStatusPub)
              │                     3. Motor analítico QCSN (aprovações, transfers e permits)
              ▼                     4. Spender revogado ou alto risco = NEGADO antes de abrir a carteira (code 4001)
        carteira (assinatura)    ← Só recebe o que foi autorizado pelo guardião
```

## 🛡️ Funcionalidades e Auditoria Realizada

1. **Instalação Antecipada do Hook EIP-1193 (`document_start`)**:
   - O `content.js` injeta o `zeus_hook.js` no mundo da página no ponto `document_start`.
   - Armadilha síncrona `Object.defineProperty(window, "ethereum")` garante que, assim que a MetaMask ou qualquer carteira injetar o provider, o wrapper EIP-1193 é aplicado **antes** que os scripts do dApp interajam com `window.ethereum`.
   - Suporte completo a injeção via eventos EIP-6963 (`eip6963:announceProvider`) e `ethereum#initialized`.

2. **Intercepção de Assinaturas e Permits (EIP-712 / EIP-2612 / Permit2)**:
   - Suporte a `eth_sendTransaction`, `eth_signTransaction`, `eth_signTypedData`, `eth_signTypedData_v1`, `eth_signTypedData_v3`, `eth_signTypedData_v4`, `personal_sign` e `eth_sign`.
   - Intercepta assinaturas off-chain de `Permit` / `Permit2` analisando a mensagem EIP-712: verifica se o `spender` / `operator` está revogado no contrato on-chain ZEUS V6 hardened antes de passar a assinatura para a carteira.

3. **Bloqueio EIP-1193 com Código Standard 4001**:
   - Transações e assinaturas rejeitadas pelo guardião ou canceladas pelo usuário em alertas não chamam o método original da carteira (`orig(args)` NUNCA é executado).
   - Lança um erro EIP-1193 com `code: 4001` (`User Rejected Request / Policy Blocked`), perfeitamente compatível com `ethers.js`, `viem` e `web3.js`.

4. **Modos de Indisponibilidade: Fail-Open Declarado & Fail-Closed Opcional**:
   - **Fail-Open (Padrão Declarado)**: Se o RPC da Arbitrum Sepolia ou o Guardião estiverem offline/indisponíveis, a extensão emite um aviso no painel e libera a transação para a carteira não travar a experiência do usuário.
   - **Fail-Closed (Opcional)**: Pode ser ativado via `window.__ZEUS_FAIL_MODE = "FAIL_CLOSED"` ou `localStorage.setItem("ZEUS_FAIL_MODE", "FAIL_CLOSED")`. Se o RPC/Guardião falhar, a transação é bloqueada por segurança com código 4001.

5. **Permissões Mínimas no Manifest V3**:
   - Permissão `"storage"` adicionada para salvar preferências do usuário.
   - Configuração `"all_frames": true` para garantir interceptação em dApps executados dentro de `iframe`s ou widgets.

---

## 🧪 Test Harness Reproduzível

Um conjunto completo de testes automatizados em Node.js valida todos os fluxos de bloqueio, passagem, intercepção de assinatura e indisponibilidade do RPC:

```bash
# Executar a suíte de testes da extensão
node ext/test_extension.js
```

### Casos de Teste Cobertos:
1. `Instalação e wrapping antecipado do provider EIP-1193`
2. `Bloqueio de eth_sendTransaction para spender revogado (código 4001, sem chamada à carteira)`
3. `Bloqueio de eth_signTypedData_v4 para permit de spender revogado (código 4001)`
4. `Passagem de transação legítima (LIBERAR) até a carteira`
5. `Cancelamento de alerta de assinatura arriscada (eth_sign cega) pelo usuário (código 4001)`
6. `Indisponibilidade do RPC em modo FAIL_OPEN (libera transação para a carteira)`
7. `Indisponibilidade do RPC em modo FAIL_CLOSED (bloqueia transação com código 4001)`
8. `Instalação automática via atribuição window.ethereum = provider (Object.defineProperty trap)`
9. `Bloqueio de assinatura Permit2 (EIP-712 PermitSingle) para spender revogado (código 4001)`
10. `Bloqueio de transação de permit on-chain para spender revogado (código 4001, sem chamada à carteira)`

---

## ⚠️ Limitações Conhecidas

1. **Provedores Não-EIP-1193 / RPC Direto**:
   - DApps que utilizem bibliotecas com signers locais rodando chave privada direta via HTTP RPC ou WebSocket sem passar pelo `window.ethereum` (EIP-1193 / EIP-6963) não são interceptados pela extensão do navegador.
2. **Indisponibilidade de RPC no Modo Fail-Open**:
   - No modo padrão (`FAIL_OPEN`), falhas de conexão com o RPC da Arbitrum Sepolia resultam na liberação da transação para a carteira do usuário. Para ambientes com política de segurança estrita, recomenda-se configurar o modo `FAIL_CLOSED` (`window.__ZEUS_FAIL_MODE = "FAIL_CLOSED"`).

---

## 📁 Arquivos da Extensão

- `manifest.json` — Manifest V3, `all_frames: true`, permissão `storage`.
- `content.js` — Injeção antecipada no mundo da página (`document_start`).
- `zeus_hook.js` — Hook EIP-1193 completo: armadilha de injeção, motor QCSN, suporte a `eth_signTypedData_v4`, modos fail-open/fail-closed e código 4001.
- `test_extension.js` — Test harness em Node.js com testes reproduzíveis sem dependências externas.
- `README.md` — Documentação completa de auditoria, arquitetura e instruções de teste.
