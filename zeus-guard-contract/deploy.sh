#!/usr/bin/env bash
# =============================================================================
# ZEUS GUARD v6 — PIPELINE DE DEPLOY STYLUS (Arbitrum Sepolia)
# =============================================================================
# Automatiza: testes -> cargo stylus check -> deploy -> init_oracle(multisig
# 2-de-3) -> verificacao on-chain -> registro do deploy.
#
# Requisitos:
#   - Rust + target wasm32-unknown-unknown:  rustup target add wasm32-unknown-unknown
#   - cargo-stylus:                          cargo install cargo-stylus
#   - Foundry (cast):                        https://getfoundry.sh
#
# Variaveis de ambiente (ou arquivo ../.env — env da shell vence):
#   DEPLOYER_PRIVATE_KEY   obrigatorio — chave da carteira deployer com ETH na
#                          Arbitrum Sepolia (0x + 64 hex). NUNCA comite.
#   MULTISIG_ORACLE_1..3   obrigatorios — enderecos PUBLICOS do conjunto multisig
#                          (generate_keys.py; threshold on-chain = 2).
#   ZEUS_RPC               opcional — default: https://sepolia-rollup.arbitrum.io/rpc
#
# Ao final, imprime o ZEUS_CONTRACT_ADDRESS para o .env do engine/oracle_service.py.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# carrega ../.env se existir (nao sobrescreve variaveis ja exportadas)
if [ -f ../.env ]; then
  set -a; . ../.env; set +a
fi

RPC="${ZEUS_RPC:-https://sepolia-rollup.arbitrum.io/rpc}"
DEPLOYER_PRIVATE_KEY="${DEPLOYER_PRIVATE_KEY:-}"
O1="${MULTISIG_ORACLE_1:-}"
O2="${MULTISIG_ORACLE_2:-}"
O3="${MULTISIG_ORACLE_3:-}"

fail() { echo "✘ $*" >&2; exit 1; }
step() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

# ---- 0. pre-flight: chaves, oraculos e ferramentas ----
step "0/6 Pre-flight"

[ "$DEPLOYER_PRIVATE_KEY" != "" ] || fail "defina DEPLOYER_PRIVATE_KEY (carteira deployer com ETH na Sepolia)"
[[ "$DEPLOYER_PRIVATE_KEY" =~ ^0x[0-9a-fA-F]{64}$ ]] || fail "DEPLOYER_PRIVATE_KEY invalido (formato: 0x + 64 hex) — cole a chave real, nao o placeholder do .env.example"
[ "${#DEPLOYER_PRIVATE_KEY}" -gt 0 ] && [ -z "${DEPLOYER_PRIVATE_KEY//[!xX]/}" ] || true

for o in O1 O2 O3; do
  val="${!o}"
  [[ "$val" =~ ^0x[0-9a-fA-F]{40}$ ]] || fail "defina ${o} (endereco publico 0x + 40 hex, de generate_keys.py)"
done
[ "$O1" != "$O2" ] && [ "$O1" != "$O3" ] && [ "$O2" != "$O3" ] || fail "os 3 oraculos precisam ser enderecos distintos"

command -v cargo >/dev/null 2>&1 || fail "cargo ausente — instale o Rust (rustup)"
cargo stylus --version >/dev/null 2>&1 || fail "cargo-stylus ausente — rode: cargo install cargo-stylus"
command -v cast >/dev/null 2>&1 || fail "cast ausente — instale o Foundry: https://getfoundry.sh"

echo "ferramentas ok | RPC: $RPC"
echo "oraculos multisig (threshold 2-de-3): $O1, $O2, $O3"

# ---- 1. testes nativos (a fortaleza so sai da fabrica com CI verde) ----
step "1/6 Testes nativos (cargo test)"
cargo test

# ---- 2. validacao WASM (binário otimizado; o gate registra o tamanho real do v6) ----
step "2/6 cargo stylus check (binario WASM otimizado)"
cargo stylus check --endpoint "$RPC"

# ---- 3. deploy ----
step "3/6 cargo stylus deploy (Stylus, Arbitrum Sepolia)"
DEPLOY_LOG="$(mktemp)"
trap 'rm -f "$DEPLOY_LOG"' EXIT
cargo stylus deploy --no-verify --max-fee-per-gas-gwei 0.1 --private-key "$DEPLOYER_PRIVATE_KEY" --endpoint "$RPC" 2>&1 | tee "$DEPLOY_LOG"

# captura o endereco do contrato (exatamente 40 hex — tx hashes tem 64 e nao casam)
CONTRACT="$(grep -oE '0x[a-fA-F0-9]{40}\b' "$DEPLOY_LOG" | tail -n1 || true)"
[ -n "$CONTRACT" ] || fail "nao capturei o endereco do contrato no output do deploy (veja o log acima)"
echo "contrato v6 deployado: $CONTRACT"

# ---- 4. init_oracle(multisig 2-de-3) ----
step "4/6 init_oracle([oracle1, oracle2, oracle3])"
cast send "$CONTRACT" "initOracle(address[])" "[$O1,$O2,$O3]" \
  --rpc-url "$RPC" --private-key "$DEPLOYER_PRIVATE_KEY"

# ---- 5. verificacao on-chain ----
step "5/6 Verificacao on-chain"
echo "oracles_pub():"
cast call "$CONTRACT" "oraclesPub()(address[])" --rpc-url "$RPC"
echo "oracle_threshold_pub():"
THRESHOLD="$(cast call "$CONTRACT" "oracleThresholdPub()(uint256)" --rpc-url "$RPC")"
echo "$THRESHOLD"
[ "$(cast --to-base "$THRESHOLD" 10 2>/dev/null || echo "$THRESHOLD")" = "2" ] \
  || [ "$THRESHOLD" = "2" ] \
  || fail "threshold on-chain nao retornou 2 — confira o init_oracle no explorer"
echo "verificado: conjunto multisig ativo com threshold 2"

# ---- 6. registro do deploy (padrao do repo) ----
step "6/6 Registro do deploy"
DATE="$(date +'%d/%m/%Y %H:%M %Z')"
cat > ../deploy/DEPLOYADO_V6_ARBITRUM_SEPOLIA.md <<EOF
# Deploy v6 — Enforceamento Absoluto (Nota 10)

**Data:** ${DATE}
**Contrato v6:** \`${CONTRACT}\`
**Rede:** Arbitrum Sepolia (chain_id 421614) — Stylus
**Explorer:** https://sepolia.arbiscan.io/address/${CONTRACT}

## O que esta versao trava

- **Enforcement absoluto:** \`vault_send\` exige nonce + bundle de assinaturas do
  oraculo (multisig 2-de-3) — o oraculo esta NO CAMINHO DO DINHEIRO.
- **Domain separation:** hash assinado inclui chain_id + address(this)
  (espelho eth_abi de 256 bytes — replay cross-chain/cross-deploy morto).
- **Rotacao de chave:** \`update_oracle_key(antiga, nova)\` pelo \`contract_owner\`.
- **Motor real:** score via /score do oraculo (features reais RPC + argmin).

## Conjunto multisig registrado (init_oracle)

| Oracul | Endereco publico |
|--------|------------------|
| 1 | \`${O1}\` |
| 2 | \`${O2}\` |
| 3 | \`${O3}\` |

Threshold on-chain: **2** (\`oracle_threshold_pub()\`).

## Proxima etapa

\`\`\`bash
export ZEUS_GUARD_CONTRACT_ADDRESS=${CONTRACT}
python3 proof/test_integration_v4.py   # prova Forged-Risk + bundle-swap + replay
\`\`\`

E no \`.env\` do \`engine/oracle_service.py\`:

\`\`\`
ZEUS_CONTRACT_ADDRESS=${CONTRACT}
\`\`\`
EOF
echo "registro salvo: deploy/DEPLOYADO_V6_ARBITRUM_SEPOLIA.md"

echo
echo "=============================================================="
echo "DEPLOY v6 COMPLETO"
echo "Contrato: ${CONTRACT}"
echo "Adicione ao .env do oracle_service.py:"
echo "  ZEUS_CONTRACT_ADDRESS=${CONTRACT}"
echo "Explorer: https://sepolia.arbiscan.io/address/${CONTRACT}"
echo "Prova red-team: ZEUS_GUARD_CONTRACT_ADDRESS=${CONTRACT} python3 proof/test_integration_v4.py"
echo "=============================================================="
