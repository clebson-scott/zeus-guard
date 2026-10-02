/**
 * Test Harness Reproduzível para ZEUS GUARD Extension (MV3 + EIP-1193)
 * Executável via: node ext/test_extension.js
 */

const assert = require("assert");

// Simulação de ambiente DOM global básico para Node.js
function setupMockWindow() {
  const events = {};
  const mockWindow = {
    listeners: events,
    addEventListener(name, fn) {
      if (!events[name]) events[name] = [];
      events[name].push(fn);
    },
    dispatchEvent(event) {
      if (events[event.type]) {
        events[event.type].forEach(fn => fn(event));
      }
    },
    __ZEUS_FAIL_MODE: "FAIL_OPEN",
    __ZEUS_AUTO_CONFIRM: undefined,
    __ZEUS_MOCK_RPC: null,
  };

  const mockDocument = {
    body: {
      appendChild(el) { mockDocument.elements.push(el); return el; },
      removeChild(el) { mockDocument.elements = mockDocument.elements.filter(e => e !== el); }
    },
    elements: [],
    getElementById(id) {
      return mockDocument.elements.find(e => e.id === id) || null;
    },
    createElement(tag) {
      return {
        tag,
        id: "",
        style: {},
        innerHTML: "",
        parentNode: mockDocument.body,
        remove() {
          mockDocument.elements = mockDocument.elements.filter(e => e !== this);
        },
        querySelector(sel) {
          return { onclick: null };
        }
      };
    }
  };

  global.window = mockWindow;
  global.document = mockDocument;
  return { mockWindow, mockDocument };
}

// Auxiliar para criar carteira simulada (EIP-1193 provider)
function createMockProvider() {
  let calls = [];
  const originalRequest = async function (args) {
    calls.push(args);
    return "0x_tx_hash_success";
  };
  const provider = {
    calls,
    originalRequest,
    request: originalRequest
  };
  return provider;
}

// Dados de teste
const USER = "0x1111111111111111111111111111111111111111";
const REVOKED_SPENDER = "0x9999999999999999999999999999999999999999";
const SAFE_SPENDER = "0x2222222222222222222222222222222222222222";
const TOKEN = "0x96fa5cea89e749e30686084a1be522ec7d12dab9"; // mUSDG

async function runTests() {
  console.log("=================================================");
  console.log("🚀 Executando Test Harness da Extensão ZEUS GUARD");
  console.log("=================================================\n");

  let passed = 0;
  let failed = 0;

  async function test(name, fn) {
    setupMockWindow();
    delete require.cache[require.resolve("./zeus_hook.js")];
    const zeusHook = require("./zeus_hook.js");
    assert.strictEqual(zeusHook.ZEUS_V6, "0x9b7608536a9704e120f0fc2c6722e2abb0fef848", "Extensão deve apontar para o V6 hardened canônico");

    try {
      await fn(zeusHook);
      console.log(`  ✅ [PASS] ${name}`);
      passed++;
    } catch (err) {
      console.error(`  ❌ [FAIL] ${name}`);
      console.error(`     Error: ${err.message}`);
      if (err.stack) console.error(`     Stack: ${err.stack.split("\n")[1]}`);
      failed++;
    }
  }

  // --- Teste 1: Instalação e Wrapping de Provider EIP-1193 ---
  await test("Instalação e wrapping antecipado do provider EIP-1193", async (hook) => {
    const provider = createMockProvider();
    window.ethereum = provider;
    hook.wrapEthereum(window.ethereum);

    assert.strictEqual(window.ethereum.__zeus, true, "Provider deve ser marcado com __zeus = true");
    assert.notStrictEqual(window.ethereum.request, provider.originalRequest, "Metodo request deve ter sido sobrescrito pelo wrapper");
  });

  // --- Teste 2: Bloqueio de Transação com Spender Revogado (code 4001 antes da carteira) ---
  await test("Bloqueio de eth_sendTransaction para spender revogado (código 4001, sem chamada à carteira)", async (hook) => {
    const provider = createMockProvider();
    hook.wrapEthereum(provider);

    window.__ZEUS_MOCK_RPC = async (method, params) => {
      if (method === "eth_call") {
        return "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001";
      }
      return "0x0";
    };

    const approveData = "0x095ea7b3" + REVOKED_SPENDER.slice(2).padStart(64, "0") + "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff";

    let thrownError = null;
    try {
      await provider.request({
        method: "eth_sendTransaction",
        params: [{ from: USER, to: TOKEN, data: approveData }]
      });
    } catch (e) {
      thrownError = e;
    }

    assert.ok(thrownError, "Transação deveria ter sido bloqueada e lançado erro");
    assert.strictEqual(thrownError.code, 4001, "Erro deve conter code 4001 (EIP-1193 rejection)");
    assert.ok(thrownError.message.includes("ZEUS GUARD: transação bloqueada"), "Mensagem de erro deve indicar bloqueio do ZEUS GUARD");
    assert.strictEqual(provider.calls.length, 0, "A carteira original NUNCA deve ter sido chamada");
  });

  // --- Teste 3: Intercepção e Bloqueio de Assinatura Permit (eth_signTypedData_v4) ---
  await test("Bloqueio de eth_signTypedData_v4 para permit de spender revogado (código 4001)", async (hook) => {
    const provider = createMockProvider();
    hook.wrapEthereum(provider);

    window.__ZEUS_MOCK_RPC = async (method, params) => {
      if (method === "eth_call") {
        return "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001";
      }
      return "0x0";
    };

    const typedDataPermit = {
      domain: { verifyingContract: TOKEN, chainId: 421614 },
      primaryType: "Permit",
      message: {
        owner: USER,
        spender: REVOKED_SPENDER,
        value: "1000000000000000000000",
        nonce: 0,
        deadline: 9999999999
      }
    };

    let thrownError = null;
    try {
      await provider.request({
        method: "eth_signTypedData_v4",
        params: [USER, JSON.stringify(typedDataPermit)]
      });
    } catch (e) {
      thrownError = e;
    }

    assert.ok(thrownError, "Assinatura de Permit deveria ter sido bloqueada");
    assert.strictEqual(thrownError.code, 4001, "Erro deve conter code 4001");
    assert.ok(thrownError.message.includes("ZEUS GUARD: assinatura bloqueada"), "Mensagem de erro deve indicar bloqueio de assinatura");
    assert.strictEqual(provider.calls.length, 0, "A carteira original NUNCA deve ter sido chamada");
  });

  // --- Teste 4: Passagem (LIBERAR) de Transação Legítima ---
  await test("Passagem de transação legítima (LIBERAR) até a carteira", async (hook) => {
    const provider = createMockProvider();
    hook.wrapEthereum(provider);

    window.__ZEUS_MOCK_RPC = async (method, params) => {
      if (method === "eth_call") return "0x00"; // Nao revogado
      if (method === "eth_getCode") return "0x1234"; // EOA false (contrato conhecido)
      if (method === "eth_getTransactionCount") return "0x64"; // 100 txs (estabelecido)
      return "0x0";
    };

    const res = await provider.request({
      method: "eth_sendTransaction",
      params: [{ from: USER, to: SAFE_SPENDER, value: "0x100", data: "0x" }]
    });

    assert.strictEqual(res, "0x_tx_hash_success", "Transação deve ser concluída com sucesso na carteira");
    assert.strictEqual(provider.calls.length, 1, "A carteira original DEVE ter sido chamada exatamente 1 vez");
  });

  // --- Teste 5: Alerta com Cancelamento pelo Usuário (code 4001) ---
  await test("Cancelamento de alerta de assinatura arriscada (eth_sign cega) pelo usuário (código 4001)", async (hook) => {
    const provider = createMockProvider();
    hook.wrapEthereum(provider);

    window.__ZEUS_AUTO_CONFIRM = false; // Usuario clica 'Cancelar' no painel de alerta

    let thrownError = null;
    try {
      await provider.request({
        method: "eth_sign",
        params: [USER, "0xdeadbeef"]
      });
    } catch (e) {
      thrownError = e;
    }

    assert.ok(thrownError, "Assinatura recusada pelo usuário deve lançar erro");
    assert.strictEqual(thrownError.code, 4001, "Erro de cancelamento deve ter code 4001");
    assert.ok(thrownError.message.includes("usuário cancelou"), "Mensagem deve mencionar cancelamento pelo usuário");
    assert.strictEqual(provider.calls.length, 0, "A carteira NUNCA deve ter sido chamada ao cancelar");
  });

  // --- Teste 6: Comportamento quando Guardião/RPC Falha - Modo FAIL_OPEN ---
  await test("Indisponibilidade do RPC em modo FAIL_OPEN (libera transação para a carteira)", async (hook) => {
    const provider = createMockProvider();
    hook.wrapEthereum(provider);

    window.__ZEUS_FAIL_MODE = "FAIL_OPEN";
    window.__ZEUS_MOCK_RPC = async () => {
      throw new Error("RPC Network Timeout / Down");
    };

    const res = await provider.request({
      method: "eth_sendTransaction",
      params: [{ from: USER, to: SAFE_SPENDER, value: "0x100" }]
    });

    assert.strictEqual(res, "0x_tx_hash_success", "Em fail-open, transação deve prosseguir para a carteira");
    assert.strictEqual(provider.calls.length, 1, "A carteira original deve ter sido chamada em fail-open");
  });

  // --- Teste 7: Comportamento quando Guardião/RPC Falha - Modo FAIL_CLOSED ---
  await test("Indisponibilidade do RPC em modo FAIL_CLOSED (bloqueia transação com código 4001)", async (hook) => {
    const provider = createMockProvider();
    hook.wrapEthereum(provider);

    window.__ZEUS_FAIL_MODE = "FAIL_CLOSED";
    window.__ZEUS_MOCK_RPC = async () => {
      throw new Error("RPC Network Timeout / Down");
    };

    let thrownError = null;
    try {
      await provider.request({
        method: "eth_sendTransaction",
        params: [{ from: USER, to: SAFE_SPENDER, value: "0x100" }]
      });
    } catch (e) {
      thrownError = e;
    }

    assert.ok(thrownError, "Em fail-closed com RPC offline, transação deve ser retida");
    assert.strictEqual(thrownError.code, 4001, "Erro deve conter code 4001");
    assert.ok(thrownError.message.includes("modo fail-closed"), "Mensagem deve indicar fail-closed");
    assert.strictEqual(provider.calls.length, 0, "A carteira NUNCA deve ser chamada em fail-closed");
  });

  // --- Teste 8: Instalação automática via atribuição window.ethereum = provider ---
  await test("Instalação automática via atribuição window.ethereum = provider (Object.defineProperty trap)", async (hook) => {
    const provider = createMockProvider();
    window.ethereum = provider;
    assert.strictEqual(window.ethereum.__zeus, true, "Provider atribuído via setter deve ser embrulhado automaticamente");
    assert.notStrictEqual(window.ethereum.request, provider.originalRequest, "Método request deve ter sido substituído pelo wrapper");
  });

  // --- Teste 9: Intercepção e Bloqueio de Assinatura Permit2 (EIP-712 PermitSingle) ---
  await test("Bloqueio de assinatura Permit2 (EIP-712 PermitSingle) para spender revogado (código 4001)", async (hook) => {
    const provider = createMockProvider();
    hook.wrapEthereum(provider);

    window.__ZEUS_MOCK_RPC = async (method, params) => {
      if (method === "eth_call") {
        return "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001";
      }
      return "0x0";
    };

    const permit2Data = {
      domain: { verifyingContract: TOKEN, chainId: 421614 },
      primaryType: "PermitSingle",
      message: {
        details: { token: TOKEN, amount: "1000000000000000000", expiration: "9999999999", nonce: "0" },
        spender: REVOKED_SPENDER,
        sigDeadline: "9999999999"
      }
    };

    let thrownError = null;
    try {
      await provider.request({
        method: "eth_signTypedData_v4",
        params: [USER, JSON.stringify(permit2Data)]
      });
    } catch (e) {
      thrownError = e;
    }

    assert.ok(thrownError, "Assinatura Permit2 deveria ter sido bloqueada");
    assert.strictEqual(thrownError.code, 4001, "Erro deve conter code 4001");
    assert.ok(thrownError.message.includes("ZEUS GUARD: assinatura bloqueada"), "Mensagem de erro deve indicar bloqueio de assinatura");
    assert.strictEqual(provider.calls.length, 0, "A carteira NUNCA deve ser chamada");
  });

  // --- Teste 10: Bloqueio de Transação de Permit On-Chain para Spender Revogado ---
  await test("Bloqueio de transação de permit on-chain para spender revogado (código 4001, sem chamada à carteira)", async (hook) => {
    const provider = createMockProvider();
    hook.wrapEthereum(provider);

    window.__ZEUS_MOCK_RPC = async (method, params) => {
      if (method === "eth_call") {
        return "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001";
      }
      return "0x0";
    };

    const permitTxData = "0xd505accf" +
      USER.slice(2).padStart(64, "0") +
      REVOKED_SPENDER.slice(2).padStart(64, "0") +
      "00000000000000000000000000000000000000000000000000000000000000ff" +
      "00000000000000000000000000000000000000000000000000000000ffffffff";

    let thrownError = null;
    try {
      await provider.request({
        method: "eth_sendTransaction",
        params: [{ from: USER, to: TOKEN, data: permitTxData }]
      });
    } catch (e) {
      thrownError = e;
    }

    assert.ok(thrownError, "Transação de permit on-chain para spender revogado deveria ter sido bloqueada");
    assert.strictEqual(thrownError.code, 4001, "Erro deve conter code 4001");
    assert.ok(thrownError.message.includes("ZEUS GUARD: transação bloqueada"), "Mensagem deve indicar bloqueio pelo ZEUS GUARD");
    assert.strictEqual(provider.calls.length, 0, "A carteira NUNCA deve ser chamada");
  });

  console.log("\n-------------------------------------------------");
  console.log(`📊 Resultado dos Testes: ${passed} passaram, ${failed} falharam.`);
  console.log("-------------------------------------------------\n");

  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch(err => {
  console.error("Erro fatal nos testes:", err);
  process.exit(1);
});
