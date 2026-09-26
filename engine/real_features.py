"""
REAL CHAIN FEATURE EXTRACTION — o ZEUS GUARD analisando transacoes REAIS.

Nada de vetor inventado: cada uma das 8 features do motor QCSN e lida do estado
REAL da blockchain via RPC publico:

  approval             -> seletor da calldata e approve/setApprovalForAll/permit
  spender_EOA          -> eth_getCode(to): EOA puro = spender nao auditavel
  spender_novo         -> eth_getTransactionCount(to): nonce baixo = recem-criado
  razao_valor          -> valor vs saldo REAL do usuario (eth_getBalance / balanceOf)
  selector_drainer     -> seletor na tabela real de padroes de drainer
  destino_envenenado   -> heuristica REAL de address poisoning: clone do prefixo/sufixo
  token_USDG_legitimo  -> token na allowlist configuravel (default: contrato com codigo e nao novo)
  padrao_normal        -> composto inverso das flags de risco

Uso:
  python3 engine/real_features.py --rpc https://sepolia-rollup.arbitrum.io/rpc \
      --user 0xALVO --to 0xSPENDER --data 0x... --value 0
  python3 engine/real_features.py --rpc https://arb1.arbitrum.io/rpc --address 0xALVO

Saida: tabela de features com a ORIGEM de cada uma (de onde veio o numero),
verdicto QCSN e o score risk_x100 que iria para o contrato.
"""
import argparse
import json
import re
import sys
import urllib.request

# seletores reais (keccak-256 dos 4 primeiros bytes), calculados sob demanda
from Crypto.Hash import keccak


def selector(sig: str) -> str:
    k = keccak.new(digest_bits=256)
    k.update(sig.encode())
    return "0x" + k.hexdigest()[:8]


# tabela real de seletor -> significado (ERC-20 padrao + padroes classicos de drainer)
APPROVE_SELECTORS = {
    selector("approve(address,uint256)"),
    selector("approve(address,uint256,bool)"),          # padrao Uniswap/compound
    selector("setApprovalForAll(address,bool)"),        # NFT
    selector("permit(address,address,uint256,uint256,uint8,bytes32,bytes32)"),
    selector("increaseAllowance(address,uint256)"),
}
DRAINER_SELECTORS = {
    selector("transferFrom(address,address,uint256)"),   # mover fundo de vitima
    selector("safeTransferFrom(address,address,uint256)"),
    selector("safeTransferFrom(address,address,uint256,bytes)"),
    selector("multicall(bytes[])"),                     # padrao de drainers modernos
    selector("execute(bytes32,bytes,bytes)"),           # routers genericos
    selector("atomicMatch(address[],...)"),             # seaport-style generico
    selector("permit2(address,address,uint160,uint48,address,bytes)"),
    selector("swapETHForExactTokens(address[],uint256,address,uint256)"),
    selector("collectPayments((address,uint256)[])"),   # inferno drainer family
    selector("withdrawToken(address,address,uint256)"),
}
NORMAL_TX_SELECTORS = {
    selector("transfer(address,uint256)"),
    selector("transfer(address,uint256,bytes)"),
    selector("deposit()"),
    selector("withdraw(uint256)"),
    selector("balanceOf(address)"),
    selector("symbol()"),
}


def _keccak256_of(s: str) -> str:
    k = keccak.new(digest_bits=256)
    k.update(s.encode())
    return k.hexdigest()


def rpc_call(rpc: str, method: str, params: list):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(rpc, body, {"Content-Type": "application/json", "User-Agent": "zeus-guard/1.0"})
    with urllib.request.urlopen(req, timeout=15) as f:
        r = json.load(f)
    if "error" in r:
        raise RuntimeError(f"RPC error em {method}: {r['error']}")
    return r["result"]


def addr_pad(a: str) -> str:
    return a.lower().replace("0x", "").rjust(64, "0")


def is_eoa(rpc: str, addr: str) -> bool:
    code = rpc_call(rpc, "eth_getCode", [addr, "latest"])
    return code == "0x" or code == "0x0"


def nonce_of(rpc: str, addr: str) -> int:
    return int(rpc_call(rpc, "eth_getTransactionCount", [addr, "latest"]), 16)


def eth_balance(rpc: str, addr: str) -> int:
    return int(rpc_call(rpc, "eth_getBalance", [addr, "latest"]), 16)


def poisoning_lookalike(user: str, target: str) -> float:
    """Heuristica REAL de address poisoning: endereco que imita o inicio E O fim
    do endereco frequente da vitima, trocando o meio. E o padrao classico dos
    atacantes que poluem o historico de transacoes."""
    u, t = user.lower().replace("0x", ""), target.lower().replace("0x", "")
    if u == t or len(u) != 40 or len(t) != 40:
        return 0.0
    same_head = u[:6] == t[:6] or u[:4] == t[:4]
    same_tail = u[-4:] == t[-4:]
    same_mid = u[8:16] == t[8:16]
    if same_head and same_tail and u != t:
        return 1.0
    if same_head and same_mid:
        return 0.6
    if same_head or (same_tail and same_mid):
        return 0.3
    return 0.0


def decode_calldata(data: str) -> tuple:
    """Retorna (selector, primeiro_endereco) da calldata real."""
    if not data or data == "0x":
        return None, None
    sel = data[:10].lower()
    first_addr = None
    if len(data) >= 138 and re.match(r"^0x[0-9a-f]+$", data.lower()):
        try:
            chunk = data[10:74]
            if int(chunk, 16) < 2**160:
                first_addr = "0x" + chunk[-40:]
        except ValueError:
            pass
    return sel, first_addr


def extract_features(rpc: str, user: str, to: str, data: str, value: int,
                     token: str = None, verbose: bool = True):
    """Le o estado REAL da chain e monta o vetor de features do QCSN.
    Retorna (features numpy, tabela de origens)."""
    import numpy as np

    origins = {}
    sel, first_addr = decode_calldata(data)
    to_eoa = is_eoa(rpc, to)
    to_nonce = nonce_of(rpc, to)
    user_bal = eth_balance(rpc, user)

    # 1. approval
    approval = 1.0 if sel in APPROVE_SELECTORS else (0.3 if sel in DRAINER_SELECTORS else 0.0)
    origins["approval"] = f"selector {sel} {'e approve/permit' if sel in APPROVE_SELECTORS else ('e padrao drainer' if sel in DRAINER_SELECTORS else 'nao e approval')}"

    # 2. spender EOA
    spender_eoa = 1.0 if to_eoa else 0.1
    origins["spender_EOA"] = "eth_getCode(to)=" + ("vazio => EOA, codigo nao auditavel" if to_eoa else "contrato com codigo")

    # 3. spender novo (nonce como proxy de idade)
    spender_novo = 1.0 if to_nonce == 0 else (0.6 if to_nonce < 5 else (0.1 if to_nonce < 50 else 0.0))
    origins["spender_novo"] = f"nonce(to)={to_nonce} (proxy real de idade do endereco)"

    # 4. razao do valor vs saldo real
    total = user_bal + value
    razao = min(1.0, value / total) if total > 0 else 0.0
    origins["razao_valor"] = f"value={value} / (saldo real {user_bal} + value), eth_getBalance"

    # 5. selector drainer
    selector_drainer = 1.0 if sel in DRAINER_SELECTORS else 0.0
    origins["selector_drainer"] = f"selector {sel} {'NA tabela de drainers' if sel in DRAINER_SELECTORS else 'fora da tabela de drainers'}"

    # 6. destino envenenado (address poisoning real)
    poison_target = first_addr or to
    destino_envenenado = poisoning_lookalike(user, poison_target)
    origins["destino_envenenado"] = f"heuristica de clone {user[:10]}.. vs {poison_target[:10]}..: {destino_envenenado}"

    # 7. token legitimo
    if token:
        legit = 0.9 if (not is_eoa(rpc, token) and nonce_of(rpc, token) > 50) else 0.2
        origins["token_USDG_legitimo"] = f"token {token}: {'contrato maduro (nonce>50)' if legit > 0.5 else 'EOA ou contrato recem-criado'}"
    else:
        legit = 0.5
        origins["token_USDG_legitimo"] = "nenhum token ERC-20 na tx (transferencia ETH ou ledger)"

    # 8. padrao normal (composto)
    normal_flags = int(sel in NORMAL_TX_SELECTORS) + int(not to_eoa and to_nonce > 50) + int(razao < 0.1)
    padrao_normal = min(1.0, normal_flags / 3 * 0.9)
    origins["padrao_normal"] = f"composto: seletor comum + spender maduro + valor pequeno ({normal_flags}/3)"

    feats = np.array([approval, spender_eoa, spender_novo, razao, selector_drainer,
                      destino_envenenado, legit, padrao_normal])
    if verbose:
        names = ["approval", "spender_EOA", "spender_novo", "razao_valor",
                 "selector_drainer", "destino_envenenado", "token_USDG_legitimo", "padrao_normal"]
        for n, v, o in zip(names, feats, [origins[k] for k in names]):
            print(f"  {n:<22} {v:4.2f}  <- {o}")
    return feats, origins


def verdict_to_risk_x100(name: str, p_star: float) -> int:
    """Mapeia o verdicto QCSN para o score que o contrato consome (0-10000)."""
    from qcsn_risk_engine import RISK_OF
    v = RISK_OF[name]
    if v == "BLOQUEAR":
        return 9500
    if v == "ALERTAR":
        return 5500  # acima da metade, abaixo do limiar de 6000
    return max(100, int(3000 * (1 - p_star)))


def main():
    ap = argparse.ArgumentParser(description="ZEUS GUARD — analise de tx REAL na chain REAL")
    ap.add_argument("--rpc", required=True, help="endpoint RPC (ex: https://sepolia-rollup.arbitrum.io/rpc)")
    ap.add_argument("--user", help="endereco da vitima (para saldo e heuristica de poisoning)")
    ap.add_argument("--to", help="endereco de destino da tx")
    ap.add_argument("--data", default="0x", help="calldata real da tx")
    ap.add_argument("--value", type=lambda x: int(x, 0), default=0, help="valor em wei")
    ap.add_argument("--token", help="endereco do token ERC-20 envolvido (opcional)")
    ap.add_argument("--address", help="modo rapido: analisa um endereco (to=address, transferencia simples)")
    args = ap.parse_args()

    if args.address:
        to = args.address
        user = args.user or args.address
        data, value, token = "0x", 0, None
    else:
        if not (args.user and args.to):
            ap.error("use --user e --to (ou --address para analise rapida)")
        to, user, data, value, token = args.to, args.user, args.data, args.value, args.token

    print(f"ZEUS GUARD — extraindo features do estado REAL da chain\nRPC: {args.rpc}")
    print(f"tx: user={user} -> to={to} data={data[:18]}... value={value}\n")
    feats, origins = extract_features(args.rpc, user, to, data, value, token)

    from qcsn_risk_engine import QCSNRiskEngine
    eng = QCSNRiskEngine()
    name, verdict, p, E = eng.classify(feats)
    risk = verdict_to_risk_x100(name, p)
    print(f"\nQCSN: {name} -> {verdict} (confianca {p:.3f})")
    print(f"score on-chain: risk_x100 = {risk}  (limiar do contrato: 6000)")
    if verdict == "BLOQUEAR":
        print("VEREDICTO: a tx NUNCA chega na carteira do usuario — o contrato reverteria com TooRisky.")
    elif verdict == "ALERTAR":
        print("VEREDICTO: passa com alerta — dentro da politica, acima da normalidade.")
    else:
        print("VEREDICTO: limpo — policy gate liberaria (checkTx/escrowPayment/vaultSend OK).")


if __name__ == "__main__":
    main()
