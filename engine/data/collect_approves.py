"""Coletor de dados REAIS: approves ERC-20 na Arbitrum mainnet, rotulados pelo desfecho.

Metodologia (ground truth = consequencia on-chain, nao lista negra):
  ataque  := approve para spender EOA seguido de transferFrom que zera o saldo da vitima
  benigno := approve para spender EOA que nunca foi usado abusivamente, OU approve para rota conhecida
"""
import json, time
from web3 import Web3

w3 = Web3(Web3.HTTPProvider("https://arb1.arbitrum.io/rpc", request_kwargs={"timeout": 30}))
APPROVE = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO32 = "0x" + "00"*32

latest = w3.eth.get_block("latest")["number"]
print("bloco atual:", latest)
# ~1.5 dias de historia em chunks de 10k blocos (2.5s de chain por chunk)
chunks = [(latest - 60_000 + i*10_000, latest - 60_000 + (i+1)*10_000) for i in range(6)]
approves = []
for a, b in chunks:
    try:
        logs = w3.eth.get_logs({"fromBlock": a, "toBlock": b,
                                "topics": [APPROVE]})
    except Exception as e:
        print("chunk", a, "erro:", str(e)[:60]); time.sleep(2); continue
    for lg in logs:
        spender = "0x" + lg["topics"][2].hex()[-40:]
        owner   = "0x" + lg["topics"][1].hex()[-40:]
        amount  = int(lg["data"].hex() or "0x0", 16)
        approves.append({"token": lg["address"], "owner": owner, "spender": spender,
                         "amount": str(amount), "block": lg["blockNumber"], "tx": lg["transactionHash"].hex()})
    if (a // 10_000) % 10 == 0:
        print(f"chunk {a}-{b}: total approves {len(approves)}", flush=True)

json.dump(approves, open("approves_raw.json", "w"))
print("TOTAL approves coletados:", len(approves))
