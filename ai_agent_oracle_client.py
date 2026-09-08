"""
⚡ PJM vs MISO Energy Arbitrage Oracle — Python SDK (AI agent client)
====================================================================
Automatic integration of an agent with the oracle on Arbitrum One (iExec Intel TDX):

  1. Checks the subscription status for the agent address (subscriptionExpiry)
  2. If missing/expired, purchases a tier in RLC
     (approve + purchaseSubscription, price fetched from the contract)
  3. Reads the gated signal getTelemetry() (vector + spread)
  4. Returns a routing decision: MISO cheaper → route there, PJM cheaper → route there

Quick start:
    pip install web3 eth-account
    export AGENT_PRIVATE_KEY=0x<agent_private_key>
    python ai_agent_oracle_client.py

Options:
    export AGENT_TIER=2        # tier: 0 = 1 day / 1 = 3 days (default) / 2 = 7 days
    export ARBITRUM_RPC_URL=.. # alternative RPC (optional)
"""


import os
import time

from eth_account import Account
from web3 import Web3

# ────────────────────────── Конфигурация ──────────────────────────

RPC_URL = os.environ.get("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc")

# ⚡ Контракт оракула (Arbitrum One Mainnet, chainId 42161)
ORACLE_CONTRACT_ADDRESS = Web3.to_checksum_address(
    "0x55d4E0EF665a747C43f8C67B8fd22A026c6aF326"
)

# iExec RLC (ERC-20, 9 decimals)
RLC_TOKEN_ADDRESS = Web3.to_checksum_address(
    "0xe649e6a1F2afc63ca268C2363691ceCAF75CF47C"
)

# Тариф по умолчанию: 0 = 24ч · 1 = 72ч · 2 = 7 дней
DEFAULT_TIER = int(os.environ.get("AGENT_TIER", "1"))

AI_AGENT_PRIVATE_KEY = os.environ.get("AGENT_PRIVATE_KEY", "")

# ────────────────────────── ABI ────────────────────────────────────
# Только нужные функции. БАГ-ФИКС: getTelemetry возвращает ЧЕТЫРЕ значения
# (timestampSlot, arbitrageVector, priceSpread, confidenceScore).

ORACLE_ABI = [
    {
        "inputs": [],
        "name": "getTelemetry",
        "outputs": [
            {"internalType": "uint256", "name": "timestampSlot", "type": "uint256"},
            {"internalType": "int8", "name": "arbitrageVector", "type": "int8"},
            {"internalType": "int256", "name": "priceSpread", "type": "int256"},
            {"internalType": "uint256", "name": "confidenceScore", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "isArbitrageProfitable",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "subscriptionExpiry",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint8", "name": "tier", "type": "uint8"}],
        "name": "getSubscriptionCost",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint8", "name": "tier", "type": "uint8"}],
        "name": "purchaseSubscription",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "uint8", "name": "tier", "type": "uint8"},
        ],
        "name": "purchaseSubscriptionFor",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]

RLC_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

TIER_LABELS = {
    0: "Sprinter Pass — 24 hours",
    1: "B2B Sweet Spot — 72 hours",
    2: "Infrastructure Pro — 7 days",
}


def send_transaction(w3, account, tx_built, label):
    """Signs and sends the transaction, waits for the receipt, and checks the status.."""
    tx_built["nonce"] = w3.eth.get_transaction_count(account.address)
    tx_built["gas"] = int(w3.eth.estimate_gas(tx_built) * 1.2)
    signed_tx = w3.eth.account.sign_transaction(tx_built, private_key=AI_AGENT_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)  # web3 v6 API
    print(f"   Tx [{label}]: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.get("status") != 1:
        raise RuntimeError(f"[{label}] REVERTED: {tx_hash.hex()}")
    print(f"   OK [{label}] confirmed in block {receipt['blockNumber']}")
    return receipt


def manage_ai_agent_access(w3, account, oracle_contract, rlc_contract, tier):
    print("\n[Step 1] Checking subscription status...")
    current_time = int(time.time())
    expiry = oracle_contract.functions.subscriptionExpiry(account.address).call()

    if expiry >= current_time:
        print(f"   OK subscription active until {time.ctime(expiry)}")
        return True

    price = oracle_contract.functions.getSubscriptionCost(tier).call()
    label = TIER_LABELS.get(tier, f"Tier {tier}")
    print(f"   Subscription missing/expired -> buying tier {tier} ({label})")
    print(f"   Dynamic price from contract: {price / 10**9:.2f} RLC")

    agent_balance = rlc_contract.functions.balanceOf(account.address).call()
    if agent_balance < price:
        raise RuntimeError(
            f"Insufficient RLC: need {price / 10**9:.2f}, have {agent_balance / 10**9:.2f}"
        )

    print(f"[Step 2] Approving RLC transfer ({price / 10**9:.2f} RLC to oracle)...")
    approve_tx = rlc_contract.functions.approve(oracle_contract.address, price).build_transaction(
        {"from": account.address}
    )
    send_transaction(w3, account, approve_tx, "approve RLC")

    print(f"[Step 3] Purchasing tier {tier} subscription...")
    buy_tx = oracle_contract.functions.purchaseSubscription(tier).build_transaction(
        {"from": account.address}
    )
    send_transaction(w3, account, buy_tx, "purchaseSubscription")
    print("   Subscription activated successfully!")
    return True


def fetch_telemetry_data(account, oracle_contract):
    print("\n[Step 4] Fetching gated TEE telemetry...")

    # Бесплатный тизер — диагностика до чтения гейтированных данных
    try:
        is_profitable = oracle_contract.functions.isArbitrageProfitable().call()
        if is_profitable:
            print("   Teaser: arbitrage IS available, signal fresh.")
        else:
            print("   Teaser: arbitrage NOT available (maintenance or stale >90 min).")
    except Exception as e:
        print(f"   Teaser unavailable: {e}")

    # Гейтированное чтение — только с активной подпиской (view, msg.sender)
    try:
        timestamp, vector, spread, confidence = oracle_contract.functions.getTelemetry().call(
            {"from": account.address}
        )
    except Exception as e:
        msg = str(e)
        if "OracleUnderMaintenance" in msg:
            print("   Oracle is in MAINTENANCE mode. Telemetry unavailable.")
        elif "SubscriptionExpired" in msg:
            print("   Subscription expired even after purchase — check contract.")
        elif "MEVReadLocked" in msg:
            print("   MEV read lock active. Retry next block.")
        elif "StaleTimestamp" in msg:
            print("   Telemetry stale (>90 min). Waiting for next TEE update.")
        else:
            print(f"   Failed to retrieve telemetry: {e}")
        return

    spread_usd_per_mwh = spread / 10**6

    print("   Signal verified by iExec TDX enclave:")
    print(f"   -> Timestamp slot : {timestamp} ({time.ctime(timestamp) if timestamp else 'N/A'})")
    print(f"   -> Arbitrage vector: {vector}  (1 = MISO cheaper | -1 = PJM cheaper | 0 = neutral)")
    print(f"   -> Price spread   : {spread_usd_per_mwh:+.2f} $/MWh  (PJM - MISO)")
    print(f"   -> Confidence     : {confidence}%")

    if vector == 1:
        print("   [AI DECISION] Route compute to MISO GPU clusters (MISO is cheaper).")
    elif vector == -1:
        print("   [AI DECISION] Route compute to PJM GPU clusters (PJM is cheaper).")
    else:
        print("   [AI DECISION] Grids balanced — no migration needed.")


if __name__ == "__main__":
    if not AI_AGENT_PRIVATE_KEY:
        raise SystemExit(
            "ERROR: AGENT_PRIVATE_KEY is not set.\n"
            "  export AGENT_PRIVATE_KEY=0x...\n"
            "  (The script refuses to run with an empty key, to avoid signing garbage.)"
        )

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to Arbitrum network.")

    account = Account.from_key(AI_AGENT_PRIVATE_KEY)
    print(f"Energy Oracle client started. Agent wallet: {account.address}")
    print(f"Oracle: {ORACLE_CONTRACT_ADDRESS} | chain: Arbitrum One (42161) | TEE: Intel TDX")

    oracle = w3.eth.contract(address=ORACLE_CONTRACT_ADDRESS, abi=ORACLE_ABI)
    rlc = w3.eth.contract(address=RLC_TOKEN_ADDRESS, abi=RLC_ABI)

    try:
        if manage_ai_agent_access(w3, account, oracle, rlc, DEFAULT_TIER):
            fetch_telemetry_data(account, oracle)
    except Exception as e:
        print(f"Critical automation failure: {e}")
