// ZEUS GUARD — hook EIP-1193. Enrola window.ethereum.request: nenhuma transacao
// ou assinatura de permit chega a carteira sem passar pelo guardiao.
// Enforcement real na camada de assinatura: o registro on-chain (approvalStatusPub)
// e consultado ANTES de assinar; spender revogado = negado automaticamente com code 4001.
(function () {
  "use strict";

  // ======== configuracao ========
  const ZEUS_V6 = "0x9b7608536a9704e120f0fc2c6722e2abb0fef848";
  const RPC = "https://sepolia-rollup.arbitrum.io/rpc";
  const CHAIN_ID_EXPECTED = "0x66eee"; // 421614

  // oraculo analitico v5: score ASSINADO off-chain antes da carteira abrir.
  // Aponte para o servidor engine/oracle_service.py em producao.
  const ORACLE_ENDPOINT = "http://localhost:8080/score";

  // seletores (keccak)
  const SEL = {
    approve: "0x095ea7b3",
    permit: "0xd505accf",
    increaseAllowance: "0x39509351",
    transfer: "0xa9059cbb",
    transferFrom: "0x23b872dd",
    approvalStatusPub: "0x35f71a52",
    balanceOf: "0x70a08231",
    totalSupply: "0x18160ddd",
  };

  // tokens legitimos conhecidos (proxy de legitimidade para a feature)
  const KNOWN_TOKENS = new Set([
    "0x980b62e83a8f971f5f6acb1aa3b0cb6aef73bfb7", // WETH arb sepolia
    "0x96fa5cea89e749e30686084a1be522ec7d12dab9", // mUSDG (nosso mock)
    "0x82af49447d8a07e3bd95bdad41225e5db2ec5aa6", // WETH arb mainnet
    "0xaf88d60669ea4743e0e50251b73b7d0f21d027e7", // USDC native
    "0xfd086d3c374c7a8b9d0a0f20d9e1e4b0b9b0f1ee", // USDT0 (aprox)
    "0xda10009cbd5d07dd09706ee15e3cf228247a8a7c", // DAI arb
    "0x2f2a2543b76a4166549f7aab2fa755c60b3b1e59", // WBTC arb
    "0x7ee8938bf7412e0a9e5b3e3b0b5e1a7d08b7c1e2", // DAI testnet (aprox)
  ].map(a => a.toLowerCase()));

  // ======== motor QCSN (caminho analitico, portado do Python v4) ========
  const ARCHETYPES = {
    DRAINER_APPROVAL: [1.0, 0.9, 0.8, 0.9, 0.9, 0.4, 0.2, 0.0],
    ADDRESS_POISONING: [0.0, 0.8, 0.7, 0.6, 0.1, 0.95, 0.3, 0.0],
    RISKY_BUT_LEGIT: [0.7, 0.3, 0.4, 0.5, 0.0, 0.0, 0.6, 0.5],
    LEGIT_SW: [0.2, 0.0, 0.1, 0.3, 0.0, 0.0, 0.8, 0.9],
    LEGIT_PAYMENT: [0.0, 0.5, 0.2, 0.4, 0.0, 0.0, 0.95, 0.8],
  };
  const RISK_OF = {
    DRAINER_APPROVAL: "BLOQUEAR", ADDRESS_POISONING: "BLOQUEAR",
    RISKY_BUT_LEGIT: "ALERTAR", LEGIT_SW: "LIBERAR", LEGIT_PAYMENT: "LIBERAR",
  };
  function qcsn(x) {
    let best = null, bestE = Infinity;
    for (const [name, prof] of Object.entries(ARCHETYPES)) {
      let e = 0;
      for (let i = 0; i < 8; i++) e += (prof[i] - x[i]) ** 2;
      if (e < bestE) { bestE = e; best = name; }
    }
    return { verdict: RISK_OF[best], archetype: best, cost: bestE };
  }

  // ======== Modo de falha: FAIL_OPEN vs FAIL_CLOSED ========
  function getFailMode() {
    try {
      if (typeof window !== "undefined" && window.__ZEUS_FAIL_MODE) {
        return String(window.__ZEUS_FAIL_MODE).toUpperCase();
      }
      if (typeof localStorage !== "undefined" && localStorage.getItem("ZEUS_FAIL_MODE")) {
        return String(localStorage.getItem("ZEUS_FAIL_MODE")).toUpperCase();
      }
    } catch {}
    return "FAIL_CLOSED"; // Seguro por padrão; FAIL_OPEN exige opt-in explícito
  }

  // ======== RPC ========
  async function rpc(method, params) {
    if (typeof window !== "undefined" && window.__ZEUS_MOCK_RPC) {
      return window.__ZEUS_MOCK_RPC(method, params);
    }
    const r = await fetch(RPC, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: Date.now(), method, params }),
    });
    if (!r.ok) throw new Error(`RPC HTTP ${r.status}`);
    const j = await r.json();
    if (j.error) throw new Error(j.error.message);
    return j.result;
  }
  function padAddr(a) { return "0x000000000000000000000000" + String(a || "").toLowerCase().replace(/^0x/, ""); }
  async function isEOA(addr) { return (await rpc("eth_getCode", [addr, "latest"])) === "0x"; }
  async function nonceAt(addr) { return parseInt(await rpc("eth_getTransactionCount", [addr, "latest"]), 16); }
  async function revokedOnChain(user, spender) {
    if (!user || !spender) return false;
    const data = SEL.approvalStatusPub + padAddr(user).slice(2) + padAddr(spender).slice(2);
    try {
      const res = await rpc("eth_call", [{ to: ZEUS_V6, data }, "latest"]);
      // retorno (uint256 amount, uint64 risk, bool revoked): revoked = ultimo byte != 0
      return res !== "0x" && parseInt(res.slice(-2), 16) === 1;
    } catch (e) {
      if (getFailMode() === "FAIL_CLOSED" || getFailMode() === "CLOSED") {
        throw e;
      }
      return false;
    }
  }
  async function tokenBalance(user, token) {
    const data = SEL.balanceOf + padAddr(user).slice(2);
    try { return BigInt(await rpc("eth_call", [{ to: token, data }, "latest"])); } catch { return 0n; }
  }

  // ======== politica deterministica por agente/origem ========
  // Opcional: a dapp pode definir window.__ZEUS_POLICY antes da chamada EIP-1193.
  // A politica e local e explicita; nunca substitui o enforcement on-chain.
  function evaluatePolicy(from, to, valueHex, dataHex) {
    let policy = null;
    try { policy = (typeof window !== "undefined" && window.__ZEUS_POLICY) || null; } catch {}
    if (!policy) return null;
    const target = String(to || "").toLowerCase();
    const selector = String(dataHex || "0x").slice(0, 10).toLowerCase();
    const value = valueHex ? BigInt(valueHex) : 0n;
    const targets = Array.isArray(policy.allowedTargets) ? policy.allowedTargets.map(String).map(x => x.toLowerCase()) : null;
    const selectors = Array.isArray(policy.allowedSelectors) ? policy.allowedSelectors.map(String).map(x => x.toLowerCase()) : null;
    if (targets && !targets.includes(target)) {
      return { verdict: "BLOQUEAR", archetype: "POLICY_TARGET_DENIED", reason: "target_not_allowlisted", target };
    }
    if (selectors && !selectors.includes(selector)) {
      return { verdict: "BLOQUEAR", archetype: "POLICY_SELECTOR_DENIED", reason: "function_not_allowlisted", selector };
    }
    if (policy.maxTxValueWei !== undefined && value > BigInt(policy.maxTxValueWei)) {
      return { verdict: "BLOQUEAR", archetype: "POLICY_VALUE_LIMIT", reason: "transaction_value_limit", value: value.toString() };
    }
    return null;
  }

  // ======== analise de tx ========
  async function analyzeTx(from, to, valueHex, dataHex) {
    const policyVerdict = evaluatePolicy(from, to, valueHex, dataHex);
    if (policyVerdict) return policyVerdict;

    const x = [0, 0, 0, 0, 0, 0, 0.5, 0.5];
    const value = valueHex ? BigInt(valueHex) : 0n;
    const selector = (dataHex || "0x").slice(0, 10).toLowerCase();
    let kind = "transfer";

    if (selector === SEL.approve || selector === SEL.increaseAllowance) {
      kind = "approval";
      x[0] = 1; x[4] = 0.9;
      const spender = "0x" + dataHex.slice(34, 74);
      const amount = BigInt("0x" + (dataHex.slice(74, 138) || "0"));

      // revogacao on-chain: consulta o registro v4 ANTES de assinar
      if (await revokedOnChain(from, spender)) {
        return { verdict: "BLOQUEAR", archetype: "REVOKED_ONCHAIN", revoked: true, spender, kind };
      }

      const eoa = await isEOA(spender);
      x[1] = eoa ? 1 : 0;
      const n = await nonceAt(spender);
      x[2] = n < 5 ? 1 : n < 50 ? 0.5 : 0.1;
      if (amount >= (1n << 200n)) x[3] = 1;
      else {
        const bal = await tokenBalance(from, to);
        x[3] = bal > 0n ? Math.min(1, Number(amount * 10000n / bal) / 10000) : 0.5;
      }
      x[6] = KNOWN_TOKENS.has(to.toLowerCase()) ? 1 : 0.2;
      x[7] = eoa ? 0.1 : 0.7;
    } else if (selector === SEL.permit) {
      kind = "permit";
      x[0] = 1; x[4] = 0.9; x[1] = 0.5; x[3] = 1;
      x[6] = KNOWN_TOKENS.has(to.toLowerCase()) ? 1 : 0.2; x[7] = 0.1;
      if (dataHex && dataHex.length >= 138) {
        const spender = "0x" + dataHex.slice(98, 138);
        if (await revokedOnChain(from, spender)) {
          return { verdict: "BLOQUEAR", archetype: "REVOKED_ONCHAIN", revoked: true, spender, kind };
        }
      }
    } else if (selector === SEL.transfer || selector === SEL.transferFrom || selector === "0x") {
      kind = "transfer";
      const dest = selector === "0x" ? to : "0x" + dataHex.slice(34, 74);
      if (await revokedOnChain(from, dest)) {
        return { verdict: "BLOQUEAR", archetype: "REVOKED_ONCHAIN", revoked: true, spender: dest, kind };
      }
      const eoa = await isEOA(dest);
      x[1] = eoa ? 0.8 : 0;
      const n = await nonceAt(dest);
      x[2] = n < 5 ? 1 : n < 50 ? 0.5 : 0.1;
      x[3] = value >= (1n << 200n) ? 1 : 0.5;
      x[5] = 0; x[7] = 0.8;
    }
    const r = qcsn(x);
    return { ...r, kind, revoked: false };
  }

  // ======== analise de assinaturas (eth_signTypedData_v4, personal_sign, etc.) ========
  function parseTypedData(param) {
    if (typeof param === "string") {
      try { return JSON.parse(param); } catch { return null; }
    }
    if (typeof param === "object" && param !== null) return param;
    return null;
  }

  async function analyzeSignature(method, params) {
    let owner = null;
    let spender = null;
    let token = null;
    let value = 0n;
    let isPermit = false;

    if (method.startsWith("eth_signTypedData")) {
      let rawData = params[1];
      if (typeof params[0] === "string" && (params[0].startsWith("{") || params[0].includes("types"))) {
        rawData = params[0];
        owner = params[1];
      } else {
        owner = params[0];
      }
      const typedData = parseTypedData(rawData);
      if (typedData && typedData.message) {
        const msg = typedData.message;
        const dom = typedData.domain || {};
        token = dom.verifyingContract || null;

        // Identifica estrutura de Permit / Permit2
        if (msg.details) {
          if (!spender && msg.details.spender) spender = msg.details.spender;
          if (!token && msg.details.token) token = msg.details.token;
          if (!value && (msg.details.amount || msg.details.value)) {
            try { value = BigInt(msg.details.amount || msg.details.value); } catch {}
          }
        }
        if (msg.spender || msg.operator || msg.grantee || spender) {
          spender = spender || msg.spender || msg.operator || msg.grantee;
          isPermit = true;
        }
        if (msg.value || msg.amount || msg.allowed || value) {
          try { value = value || BigInt(msg.value || msg.amount || msg.allowed); } catch {}
        }
        if (!owner && (msg.owner || msg.holder)) {
          owner = msg.owner || msg.holder;
        }
      }
    } else if (method === "personal_sign" || method === "eth_sign") {
      if (method === "eth_sign") {
        return { verdict: "ALERTAR", archetype: "BLIND_SIGNING", kind: "eth_sign", detail: "Assinatura cega de bytes brutos (eth_sign)" };
      }
    }

    if (isPermit && spender) {
      if (owner && await revokedOnChain(owner, spender)) {
        return { verdict: "BLOQUEAR", archetype: "REVOKED_ONCHAIN", revoked: true, spender, kind: "permit_typed_data" };
      }
      // Analisa risco do permit
      const x = [1, 0, 0, 0, 0.9, 0, 0.5, 0.5];
      const eoa = await isEOA(spender);
      x[1] = eoa ? 1 : 0;
      const n = await nonceAt(spender);
      x[2] = n < 5 ? 1 : n < 50 ? 0.5 : 0.1;
      x[3] = (value >= (1n << 200n) || value === 0n) ? 1 : 0.5;
      x[6] = token && KNOWN_TOKENS.has(token.toLowerCase()) ? 1 : 0.2;
      x[7] = eoa ? 0.1 : 0.7;

      const r = qcsn(x);
      return { ...r, kind: "permit_typed_data", spender, token };
    }

    return { verdict: "LIBERAR", archetype: "LEGIT_SIGNATURE", kind: method };
  }

  // ======== UI ========
  function banner(level, msg, detail) {
    if (typeof document === "undefined") return;
    const colors = { BLOQUEAR: "#c0392b", ALERTAR: "#d68910", LIBERAR: "#1e8449" };
    let el = document.getElementById("zeus-banner");
    if (el) el.remove();
    el = document.createElement("div");
    el.id = "zeus-banner";
    el.style.cssText = `position:fixed;top:0;left:50%;transform:translateX(-50%);z-index:2147483647;
      background:#1a1a2e;color:#fff;font:13px/1.4 system-ui;padding:12px 18px;border-radius:0 0 12px 12px;
      border:2px solid ${colors[level] || "#d68910"};max-width:480px;box-shadow:0 4px 24px rgba(0,0,0,.5)`;
    el.innerHTML = `<b style="color:${colors[level] || "#d68910"}">ZEUS GUARD · ${level}</b><br>${msg}` +
      (detail ? `<br><span style="opacity:.7;font-size:11px">${detail}</span>` : "");
    (document.head || document.documentElement || document.body).appendChild(el);
    setTimeout(() => { if (el.parentNode) el.remove(); }, 6000);
  }

  function confirmWithUser(level, msg, detail) {
    if (typeof document === "undefined") return Promise.resolve(true);
    if (window.__ZEUS_AUTO_CONFIRM !== undefined) {
      return Promise.resolve(Boolean(window.__ZEUS_AUTO_CONFIRM));
    }
    return new Promise(resolve => {
      let el = document.getElementById("zeus-confirm");
      if (el) el.remove();
      el = document.createElement("div");
      el.id = "zeus-confirm";
      el.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:2147483647;background:#1a1a2e;
        color:#fff;font:13px/1.5 system-ui;padding:16px;border-radius:12px;border:2px solid #d68910;
        max-width:360px;box-shadow:0 8px 32px rgba(0,0,0,.6)`;
      el.innerHTML = `<b style="color:#d68910">ZEUS GUARD · ${level}</b><br>${msg}<br>
        ${detail ? `<span style="opacity:.7;font-size:11px">${detail}</span><br>` : ""}
        <div style="margin-top:10px;display:flex;gap:8px">
          <button id="zg-no" style="flex:1;padding:8px;border:0;border-radius:8px;background:#c0392b;color:#fff;cursor:pointer">Cancelar tx</button>
          <button id="zg-yes" style="flex:1;padding:8px;border:0;border-radius:8px;background:#1e8449;color:#fff;cursor:pointer">Assinar mesmo assim</button>
        </div>`;
      (document.head || document.documentElement || document.body).appendChild(el);
      el.querySelector("#zg-no").onclick = () => { el.remove(); resolve(false); };
      el.querySelector("#zg-yes").onclick = () => { el.remove(); resolve(true); };
    });
  }

  // ======== helper de erro EIP-1193 ========
  function buildRejectionError(msg) {
    const e = new Error(msg);
    e.code = 4001; // EIP-1193 User Rejected Request / Policy Blocked
    return e;
  }

  // ======== oraculo v5: score assinado off-chain (falha em modo de contingencia) ========
  async function oraclePreCheck(tx) {
    if (!ORACLE_ENDPOINT) return null;
    let validation = null;
    try {
      const res = await fetch(ORACLE_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user: tx.from || "0x0000000000000000000000000000000000000000",
          to: tx.to || tx.from || "0x0000000000000000000000000000000000000000",
          token: tx.token || null,
          amount: tx.value ? parseInt(tx.value, 16) : 0,
          nonce: tx.nonce ? parseInt(tx.nonce, 16) : 0,
          origin: (typeof window !== "undefined" && window.location) ? window.location.origin : "",
          raw_tx: tx
        })
      });
      if (res.ok) validation = await res.json();
    } catch (err) {
      console.error("[ZEUS GUARD] Oraculo indisponivel — operando em modo de contingencia (firewall on-chain local).", err);
      return null;
    }
    if (!validation) return null;

    // bloqueio do oraculo NUNCA vira falha silenciosa
    if (validation.verdict === "BLOQUEAR" || validation.score >= 6000) {
      const e = buildRejectionError(
        "ZEUS GUARD: transacao rejeitada pelo oraculo (score " + validation.score +
        " — padrao de drainer)"
      );
      throw e;
    }
    // metadados para o contrato validar on-chain em vault_send/check_tx_signed (v6: multisig)
    if (validation.signature) {
      tx.zeus_score = validation.score;
      tx.zeus_sig = validation.signature;      // compat
      if (validation.signatures && validation.signatures.length >= 2) {
        tx.zeus_sigs = validation.signatures;   // bundle 2-de-3 exigido pelo cofre
      }
    }
    return validation;
  }

  // ======== hook ========
  function wrapEthereum(eth) {
    if (!eth || eth.__zeus) return;
    const orig = eth.request.bind(eth);

    eth.request = async function (args) {
      const { method, params } = args || {};
      const failMode = getFailMode();

      try {
        if (method === "eth_sendTransaction" || method === "eth_signTransaction") {
          const tx = params && params[0];
          if (tx && tx.from) {
            await oraclePreCheck(tx); // v5: score assinado pelo oraculo (bloqueio = 4001)
            const r = await analyzeTx(tx.from, tx.to || "0x", tx.value, tx.data || "0x");
            if (r.verdict === "BLOQUEAR") {
              const why = r.revoked ? "spender REVOGADO no registro on-chain do ZEUS GUARD" : r.archetype;
              banner("BLOQUEAR", `Transação negada pelo guardião: ${why}`,
                `${tx.to || "contract"} · consulte sepolia.arbiscan.io/address/${ZEUS_V6}`);
              throw buildRejectionError(`ZEUS GUARD: transação bloqueada (${why})`);
            }
            if (r.verdict === "ALERTAR") {
              const ok = await confirmWithUser("ALERTAR",
                `Transação arriscada (${r.archetype}). Deseja assinar mesmo assim?`,
                `destino: ${tx.to}`);
              if (!ok) {
                throw buildRejectionError("ZEUS GUARD: usuário cancelou após alerta");
              }
            } else {
              banner("LIBERAR", `Transação liberada (${r.archetype})`, `${(tx.to || "").slice(0, 20)}…`);
            }
          }
        } else if (method.startsWith("eth_signTypedData") || method === "personal_sign" || method === "eth_sign") {
          const r = await analyzeSignature(method, params || []);
          if (r.verdict === "BLOQUEAR") {
            const why = r.revoked ? "spender REVOGADO no registro on-chain do ZEUS GUARD" : r.archetype;
            banner("BLOQUEAR", `Assinatura negada pelo guardião: ${why}`,
              `método: ${method}`);
            throw buildRejectionError(`ZEUS GUARD: assinatura bloqueada (${why})`);
          }
          if (r.verdict === "ALERTAR") {
            const ok = await confirmWithUser("ALERTAR",
              `Assinatura arriscada (${r.archetype}). Deseja assinar mesmo assim?`,
              `método: ${method} ${r.detail || ""}`);
            if (!ok) {
              throw buildRejectionError("ZEUS GUARD: usuário cancelou após alerta de assinatura");
            }
          } else {
            banner("LIBERAR", `Assinatura liberada (${r.archetype})`, `método: ${method}`);
          }
        }
      } catch (e) {
        if (e && e.code === 4001) throw e;

        // Falha no RPC / Guardião
        if (failMode === "FAIL_CLOSED" || failMode === "CLOSED") {
          banner("BLOQUEAR", "Transação negada: Guardião/RPC indisponível (modo fail-closed)",
            e.message || "Falha de comunicação com o guardião");
          throw buildRejectionError(`ZEUS GUARD: guardião indisponível (modo fail-closed)`);
        } else {
          // Fail-open declarado por padrão
          console.warn("[zeus-guard] guardiao indisponivel (fail-open):", e.message);
          banner("ALERTAR", "Guardião indisponível - liberando transação (modo fail-open)",
            e.message || "RPC offline");
        }
      }
      return orig(args);
    };

    eth.__zeus = true;
    console.log("[zeus-guard] EIP-1193 embrulhado: toda transação e permit passa pelo guardião (v6 hardened, " + ZEUS_V6 + ")");
  }

  // Instalação antecipada e robusta do hook
  function initHook() {
    if (typeof window !== "undefined" && window.ethereum && !window.ethereum.__zeus) {
      wrapEthereum(window.ethereum);
    }
  }

  if (typeof window !== "undefined") {
    // 1. Instalação imediata se window.ethereum já existir
    initHook();

    // 2. Intercepta atribuição / definição futura via Object.defineProperty
    try {
      let rawEth = window.ethereum;
      Object.defineProperty(window, "ethereum", {
        configurable: true,
        enumerable: true,
        get() {
          return rawEth;
        },
        set(val) {
          rawEth = val;
          if (val && !val.__zeus) {
            wrapEthereum(val);
          }
        }
      });
    } catch (e) {
      // Fallback para ambientes restritos
    }

    // 3. Listeners de eventos de injeção de carteiras (EIP-6963 e ethereum#initialized)
    window.addEventListener("ethereum#initialized", () => initHook(), { once: true });
    window.addEventListener("eip6963:announceProvider", (event) => {
      if (event && event.detail && event.detail.provider && !event.detail.provider.__zeus) {
        wrapEthereum(event.detail.provider);
      }
    });

    // 4. Polling rápido para captura antecipada (intervalo de 20ms)
    let tries = 0;
    const iv = setInterval(() => {
      initHook();
      if (++tries > 300) clearInterval(iv);
    }, 20);
  }

  // Export para ambiente Node / Harness de testes se disponível
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { wrapEthereum, getFailMode, ARCHETYPES, qcsn, evaluatePolicy, ZEUS_V6, SEL };
  }
})();
