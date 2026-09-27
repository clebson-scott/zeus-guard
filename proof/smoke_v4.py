import json, time
from web3 import Web3
from eth_utils import to_hex

w3 = Web3(Web3.HTTPProvider("https://sepolia-rollup.arbitrum.io/rpc"))
abi = json.load(open("/tmp/zeus-guard/zeus-guard-contract/zeus-guard-abi.json"))
err_sels = {}
for f in abi:
    if f.get("type") == "error":
        sig = f"{f['name']}({','.join(i['type'] for i in f['inputs'])})"
        err_sels[to_hex(w3.keccak(text=sig)[:4])] = f["name"]

V4_ADDR = Web3.to_checksum_address("0xa9ef4e9be0e8f45e737f361380743faab72fe76a")
ZEUS = w3.eth.contract(address=V4_ADDR, abi=abi)

key = "45cf3a9a7965ff31916c13232e7670ca1eca3ff7be3c3b6a137191229fa93da9"
acct = w3.eth.account.from_key(key)
ME = acct.address
SPENDER = Web3.to_checksum_address("0x000000000000000000000000000000000000dEaD")

results = []
def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")

def send(fn, label, expect_revert=None):
    try:
        fn.call({"from": ME})
        reason = None
    except Exception as e:
        d = str(getattr(e, "data", "") or "")
        reason = next((n for s, n in err_sels.items() if s in d), d[:50] or "revert")
    if expect_revert:
        check(label, reason == expect_revert, f"reason={reason}")
        return False
    if reason:
        check(label, False, f"unexpected revert: {reason}")
        return False
    t = {"to": ZEUS.address, "from": ME, "data": fn._encode_transaction_data(),
         "nonce": w3.eth.get_transaction_count(ME),
         "gas": 2_000_000, "maxFeePerGas": w3.to_wei(0.3, "gwei"),
         "maxPriorityFeePerGas": w3.to_wei(0.01, "gwei"), "chainId": 421614}
    s = acct.sign_transaction(t)
    h = w3.eth.send_raw_transaction(s.raw_transaction)
    r = w3.eth.wait_for_transaction_receipt(h)
    check(label, r["status"] == 1, f"tx={to_hex(h)[:16]}…")
    return r["status"] == 1

print(f"Executing Smoke Tests against v4 contract {V4_ADDR}")
print(f"user: {ME}\n")

# 1) fresh session
send(ZEUS.functions.initSession(ME, 3600, 10**24), "initSession v4 (cap=1e24)")

# 2) v4 public approval logging & public inspection
send(ZEUS.functions.logApproval(ME, SPENDER, 10**18, 10), "logApproval(user, spender, 1e18, risk=10)")
status = ZEUS.functions.approvalStatusPub(ME, SPENDER).call()
check("approvalStatusPub == (1e18, 10, False)", status[0] == 10**18 and status[1] == 10 and status[2] == False, f"got {status}")

# 3) guardian revoke
send(ZEUS.functions.guardianRevoke(ME, SPENDER), "guardianRevoke(ME, SPENDER)")
status_rev = ZEUS.functions.approvalStatusPub(ME, SPENDER).call()
check("approvalStatusPub == (1e18, 10, True)", status_rev[2] == True, f"got {status_rev}")

# 4) read firewall checks
send(ZEUS.functions.checkTx(ME, 10**18, 9000), "checkTx risk=90% BLOCKED", expect_revert="TooRisky")
send(ZEUS.functions.checkTx(ME, 10**18, 5999), "checkTx risk=59.99% passes")

# 5) escrow firewall
pid_hi = w3.keccak(text=f"v4-smoke-hi-{time.time()}")
send(ZEUS.functions.escrowPayment(pid_hi, SPENDER, 10**17, 9000), "escrow risk=90% BLOCKED", expect_revert="TooRisky")

pid_ok = w3.keccak(text=f"v4-smoke-ok-{time.time()}")
send(ZEUS.functions.escrowPayment(pid_ok, SPENDER, 10**17, 10), "escrow risk=1% passes")

# 6) dispute + refund
send(ZEUS.functions.disputePayment(pid_ok), "disputePayment on-chain")
send(ZEUS.functions.releasePayment(pid_ok), "release blocked while disputed", expect_revert="PaymentDisputed")
send(ZEUS.functions.refundDisputed(pid_ok), "refundDisputed on-chain")

# 7) typed error for > u128
send(ZEUS.functions.escrowPayment(w3.keccak(text=f"v4-smoke-big-{time.time()}"), SPENDER, 2**130, 10), "escrow > u128 typed error", expect_revert="AmountTooLarge")

print(f"\n==================================================")
print(f"SMOKE V4 RESULT: {sum(results)}/{len(results)} passed")
print(f"==================================================")
