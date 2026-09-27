"""Rotulagem por desfecho: approve seguido de pull por terceiro.

Diferenciacao estrita entre:
  - pulled_by_third_party: transferencia por terceiro (tx.from != owner) na janela de 4h
  - ATTACK: ataque de drainer confirmado (pulled por terceiro em approve ilimitado ou EOA/drainer)
  - BENIGN: sem pull por terceiro, OU operacao legitima em contrato de protocolo/DEX
"""
import json, time
from concurrent.futures import ThreadPoolExecutor
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://arb1.arbitrum.io/rpc", request_kwargs={"timeout": 30}))
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
UNLIMITED = 2**200

# Principais contratos de DEX/roteadores conhecidos na Arbitrum
KNOWN_PROTOCOLS = {
    "0xc36442b4a4522e871399cd717abdd847ab11fe88", # Uniswap V3 NonfungiblePositionManager
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45", # Uniswap V3 SwapRouter02
    "0x777777777777aec03fd955926dbf81597e66834c", # 1inch Router
    "0x111111125421ca6dc452d289314280a0f8842a65", # 1inch v5
    "0xe592427a0aece92de3edee1f18e0157c05861564", # Uniswap V3 SwapRouter
}

def pad(addr): return "0x000000000000000000000000" + addr[2:].lower()

def process(a):
    a = {k: (v.hex() if hasattr(v, 'hex') and not isinstance(v, str) else v) for k, v in a.items()}
    out = dict(a)
    owner = a["owner"]
    spender = a["spender"]
    token = a["token"]
    
    try:
        # transfers do owner do token aprovado, ate 4h apos o approve
        logs = w3.eth.get_logs({"fromBlock": a["block"], "toBlock": a["block"] + 7200,
                                "address": Web3.to_checksum_address(token),
                                "topics": [TRANSFER, pad(owner)]})
        pulled = 0
        for lg in logs:
            if lg["blockNumber"] < a["block"]: continue
            tx = w3.eth.get_transaction(lg["transactionHash"])
            if tx["from"].lower() != owner.lower():        # pull por terceiro!
                amount = int(lg["data"].hex() or "0x0", 16)
                pulled += amount
                
        amount = int(a["amount"])
        approval_unlimited = amount >= UNLIMITED
        sp_lower = spender.lower()
        is_known_proto = sp_lower in KNOWN_PROTOCOLS
        is_eoa = a.get("spender_eoa", 0) == 1
        
        # Registra o desfecho bruto
        out["pulled_by_third_party"] = pulled
        out["approval_unlimited"] = approval_unlimited
        
        # Ground truth: ATTACK = pull por terceiro em approve ilimitado ou EOA/drainer sem protocolo conhecido
        is_attack = (pulled > 0) and not is_known_proto and (approval_unlimited or (is_eoa and pulled >= 1_000_000))
        out["label"] = "ATTACK" if is_attack else "BENIGN"
        return out
    except Exception as e:
        return {"owner": owner, "error": str(e)[:50]}

if __name__ == "__main__":
    eoa_apps = json.load(open("eoa_approves.json")) if False else []
    print("Módulo label_by_outcome carregado.")
