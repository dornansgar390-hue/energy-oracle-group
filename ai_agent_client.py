import os
import time
from web3 import Web3

# --- Configuration ---
ORACLE_CONTRACT_ADDRESS = "0xcfD218DfFced67D0197E9aE3739CC11eE61C2AD6"
RLC_TOKEN_ADDRESS = "0xe649e6a1F2afc63ca268C2363691ceCAF75CF47C" # Arbitrum One Mainnet RLC
AGENT_PRIVATE_KEY = os.environ.get("AGENT_PRIVATE_KEY")
RPC_URL = "https://arb1.arbitrum.io/rpc"

# --- Contract ABIs (Compact) ---
ORACLE_ABI = [
    {"inputs":[],"name":"getTelemetry","outputs":[{"internalType":"uint256","name":"timestampSlot","type":"uint256"},{"internalType":"int8","name":"arbitrageVector","type":"int8"},{"internalType":"uint256","name":"confidenceScore","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint8","name":"tier","type":"uint8"}],"name":"purchaseSubscription","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint8","name":"tier","type":"uint8"}],"name":"purchaseSubscriptionFor","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"claimFreeTrial","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"isArbitrageProfitable","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"subscriptionExpiry","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]

ERC20_ABI = [
    {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]

def main():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise Exception("Failed to connect to the network.")

    agent_address = w3.eth.account.from_key(AGENT_PRIVATE_KEY).address
    print(f"Loaded agent address: {agent_address}")

    oracle_contract = w3.eth.contract(address=w3.to_checksum_address(ORACLE_CONTRACT_ADDRESS), abi=ORACLE_ABI)
    rlc_contract = w3.eth.contract(address=w3.to_checksum_address(RLC_TOKEN_ADDRESS), abi=ERC20_ABI)

    try:
        is_profitable = oracle_contract.functions.isArbitrageProfitable().call()
        print(f"Blind Teaser: Is arbitrage profitable right now? {is_profitable}")
    except Exception as e:
        print(f"Failed to fetch blind teaser: {e}")

    expiration_timestamp = oracle_contract.functions.subscriptionExpiry(agent_address).call()
    current_timestamp = int(time.time())

    if expiration_timestamp < current_timestamp:
        print("Subscription expired or does not exist. Purchasing Tier 1 (150 RLC)...")
        cost = 150 * 10**9
        approve_tx = rlc_contract.functions.approve(ORACLE_CONTRACT_ADDRESS, cost).build_transaction({
            'from': agent_address,
            'nonce': w3.eth.get_transaction_count(agent_address),
            'gas': 100000
        })
        signed_approve_tx = w3.eth.account.sign_transaction(approve_tx, AGENT_PRIVATE_KEY)
        approve_tx_hash = w3.eth.send_raw_transaction(signed_approve_tx.rawTransaction)
        print(f"Approve transaction sent: {approve_tx_hash.hex()}")
        w3.eth.wait_for_transaction_receipt(approve_tx_hash)

        buy_tx = oracle_contract.functions.purchaseSubscription(1).build_transaction({
            'from': agent_address,
            'nonce': w3.eth.get_transaction_count(agent_address),
            'gas': 150000
        })
        signed_buy_tx = w3.eth.account.sign_transaction(buy_tx, AGENT_PRIVATE_KEY)
        buy_tx_hash = w3.eth.send_raw_transaction(signed_buy_tx.rawTransaction)
        print(f"Subscription purchase transaction sent: {buy_tx_hash.hex()}")
        w3.eth.wait_for_transaction_receipt(buy_tx_hash)
        print("Subscription purchase confirmed!")
    else:
        print(f"Subscription is valid until {time.ctime(expiration_timestamp)}")

    try:
        timestamp_slot, arbitrage_vector, confidence_score = oracle_contract.functions.getTelemetry().call({
            'from': agent_address
        })
        print("\n--- Gated Telemetry Signals ---")
        print(f"Time-slot Slot : {timestamp_slot}")
        print(f"Arbitrage Vector: {arbitrage_vector} (1 = Shift to MISO | -1 = Shift to PJM | 0 = Neutral)")
        print(f"Confidence Score: {confidence_score}%")
        print("-------------------------------")
        
        if arbitrage_vector == 1:
            print("🤖 AI DECISION: Route computational workloads to MISO (lower cost grid).")
        elif arbitrage_vector == -1:
            print("🤖 AI DECISION: Route computational workloads to PJM (lower cost grid).")
        else:
            print("🤖 AI DECISION: Grids are balanced. No workload migration needed.")
    except Exception as e:
        print(f"\nCould not retrieve gated telemetry data: {e}")

if __name__ == "__main__":
    if not AGENT_PRIVATE_KEY:
        raise ValueError("Please set the AGENT_PRIVATE_KEY environment variable.")
    main()
