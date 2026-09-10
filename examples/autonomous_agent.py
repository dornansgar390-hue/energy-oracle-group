import os, asyncio, json
from web3 import Web3
from eth_account import Account

# Configuration
RPC_URL = os.environ.get("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc")
PRIVATE_KEY = os.environ.get("AGENT_PRIVATE_KEY")
ORACLE_ADDRESS = Web3.to_checksum_address("0x55d4E0EF665a747C43f8C67B8fd22A026c6aF326")
RLC_ADDRESS = Web3.to_checksum_address("0xe649e6a1F2afc63ca268C2363691ceCAF75CF47C")

MCP_ENDPOINT = "https://energy-arbitrage.io/mcp"
TIER = int(os.environ.get("AGENT_TIER", "1"))  # 0=24h, 1=72h, 2=7d

print(f"""
╔\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557
║  PJM vs MISO Energy Arbitrage Oracle \u2014 Autonomous Agent        ║
║  Intel TDX Attested \u00b7 Arbitrum One \u00b7 Streamable HTTP          ║
╚\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d")
print(f"Agent wallet: {Account.from_key(PRIVATE_KEY).address}" if PRIVATE_KEY else "Agent wallet: (no key set)")
print()

async def main():
    print("This script requires an MCP client library to connect via streamable-http.")
    print(f"Connect to: {MCP_ENDPOINT}")
    print()
    print("For autonomous execution, use ai_agent_oracle_client.py instead:")
    print("  pip install web3 eth-account")
    print("  export AGENT_PRIVATE_KEY=0x...")
    print("  python ai_agent_oracle_client.py")
    print()
    print("The autonomous flow is:")
    print("1. Connect MCP client to endpoint")
    print("2. Call get_oracle_status() \u2014 verify system active")
    print("3. Call is_arbitrage_profitable() \u2014 check opportunity")
    print("4. Call check_subscription(wallet) \u2014 check license")
    print("5. If no license: call build_subscription_tx(wallet, tier)")
    print("6. Sign approve(RLC) + purchaseSubscription (two tx)")
    print("7. Call get_telemetry(wallet) \u2014 read signal")

if __name__ == "__main__":
    asyncio.run(main())
