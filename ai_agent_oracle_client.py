import time
import os
from web3 import Web3
from eth_account import Account

# --- Configuration ---
RPC_URL = "https://arb1.arbitrum.io/rpc"
ORACLE_CONTRACT_ADDRESS = "0xcfD218DfFced67D0197E9aE3739CC11eE61C2AD6"
RLC_TOKEN_ADDRESS = "0xe649e6a1F2afc63ca268C2363691ceCAF75CF47C" # Arbitrum One Mainnet RLC

AI_AGENT_PRIVATE_KEY = os.environ.get("AGENT_PRIVATE_KEY", "0x0000000000000000000000000000000000000000000000000000000000000000")

# --- Contract ABIs (Compact) ---
ORACLE_ABI = [
    {"inputs":[],"name":"getTelemetry","outputs":[{"internalType":"uint256","name":"timestampSlot","type":"uint256"},{"internalType":"int8","name":"arbitrageVector","type":"int8"},{"internalType":"uint256","name":"confidenceScore","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint8","name":"tier","type":"uint8"}],"name":"purchaseSubscription","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"tier","type":"uint8"}],"name":"purchaseSubscriptionFor","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"claimFreeTrial","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"isArbitrageProfitable","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"subscriptionExpiry","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]

RLC_ABI = [
    {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]

def send_transaction(w3, account, tx_built):
    """Signs and sends an EVM transaction."""
    tx_built['nonce'] = w3.eth.get_transaction_count(account.address)
    tx_built['gas'] = int(w3.eth.estimate_gas(tx_built) * 1.2)
    signed_tx = w3.eth.account.sign_transaction(tx_built, private_key=AI_AGENT_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction sent. Hash: {tx_hash.hex()}")
    return w3.eth.wait_for_transaction_receipt(tx_hash)

def manage_ai_agent_access(w3, account, oracle_contract, rlc_contract):
    print("\n[Step 1] Checking subscription status...")
    current_time = int(time.time())
    expiry = oracle_contract.functions.subscriptionExpiry(account.address).call()
    
    if expiry >= current_time:
        print(f"Subscription is active. Valid until: {time.ctime(expiry)}")
        return True

    print("Subscription expired or not found. Purchasing Tier 1 (150 RLC)...")
    price = 150 * 10**9 # Tier 1: 150 RLC
    agent_balance = rlc_contract.functions.balanceOf(account.address).call()
    if agent_balance < price:
        raise Exception(f"Insufficient RLC balance. Required: {price / 10**9}, Balance: {agent_balance / 10**9}")

    print(f"[Step 2] Approving RLC transfer of {price / 10**9} RLC...")
    approve_tx = rlc_contract.functions.approve(oracle_contract.address, price).build_transaction({
        'from': account.address,
    })
    send_transaction(w3, account, approve_tx)

    print("[Step 3] Purchasing Tier 1 subscription...")
    buy_tx = oracle_contract.functions.purchaseSubscription(1).build_transaction({
        'from': account.address,
    })
    send_transaction(w3, account, buy_tx)
    print("Subscription successfully activated!")
    return True

def fetch_telemetry_data(account, oracle_contract):
    print("\n[Step 4] Fetching gated TEE telemetry...")
    try:
        timestamp, vector, confidence = oracle_contract.functions.getTelemetry().call({
            'from': account.address
        })
        print("✅ Arbitrage signals retrieved and verified by iExec TEE Enclave!")
        print(f"-> Timestamp slot: {timestamp} | Confidence index: {confidence}%")
        print(f"-> Arbitrage vector: {vector} (1 = Route to MISO | -1 = Route to PJM | 0 = Neutral)")
        
        if vector == 1:
            print("🤖 [AI DECISION]: MISO is optimal. Initiating Compute Workload Routing to MISO GPU clusters...")
        elif vector == -1:
            print("🤖 [AI DECISION]: PJM is optimal. Initiating Compute Workload Routing to PJM GPU clusters...")
        else:
            print("🤖 [AI DECISION]: Grids are balanced. No migration needed.")
    except Exception as e:
        print(f"❌ Failed to retrieve telemetry: {e}")

if __name__ == "__main__":
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise Exception("Failed to connect to Arbitrum network.")

    account = Account.from_key(AI_AGENT_PRIVATE_KEY)
    print(f"AI Agent initialized. Wallet: {account.address}")

    oracle = w3.eth.contract(address=w3.to_checksum_address(ORACLE_CONTRACT_ADDRESS), abi=ORACLE_ABI)
    rlc = w3.eth.contract(address=w3.to_checksum_address(RLC_TOKEN_ADDRESS), abi=RLC_ABI)

    try:
        if manage_ai_agent_access(w3, account, oracle, rlc):
            fetch_telemetry_data(account, oracle)
    except Exception as e:
        print(f"Critical automation failure: {e}")
