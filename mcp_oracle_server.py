"""
⚡ PJM vs MISO Energy Arbitrage Oracle — MCP Server (FastMCP)
=============================================================
Lets AI agents (Claude Desktop, Cursor, VS Code, any MCP client)
DISCOVER the oracle, check status/prices, get purchase transactions
and the full Python SDK right inside the conversation.

Local run (Streamable HTTP):  python mcp_oracle_server.py
Endpoint:                     https://energy-arbitrage.io/mcp
"""

import json
import os
import time
from pathlib import Path
from typing import Annotated, Optional

from pydantic import Field
from web3 import Web3
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations, Annotations, Icon

# ═══════════ Configuration ═══════════

RPC_URL = os.environ.get("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc")
ORACLE_ADDRESS = Web3.to_checksum_address("0x55d4E0EF665a747C43f8C67B8fd22A026c6aF326")
RLC_ADDRESS = Web3.to_checksum_address("0xe649e6a1F2afc63ca268C2363691ceCAF75CF47C")
CHAIN_ID = 42161
PUBLIC_ENDPOINT = "https://energy-arbitrage.io/mcp"
HOMEPAGE = "https://energy-arbitrage.io"
VERSION = "1.3.1"

# Server uptime tracking
START_TIME = time.time()

TIERS = {
    0: {"name": "Sprinter Pass", "duration": "24 hours", "usd": 20},
    1: {"name": "B2B Sweet Spot", "duration": "72 hours", "usd": 50},
    2: {"name": "Infrastructure Pro", "duration": "7 days", "usd": 100},
}

ORACLE_ABI = [
    {"inputs": [], "name": "getTelemetry", "outputs": [
        {"internalType": "uint256", "name": "timestampSlot", "type": "uint256"},
        {"internalType": "int8", "name": "arbitrageVector", "type": "int8"},
        {"internalType": "int256", "name": "priceSpread", "type": "int256"},
        {"internalType": "uint256", "name": "confidenceScore", "type": "uint256"},
    ], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "isArbitrageProfitable", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint8", "name": "tier", "type": "uint8"}], "name": "getSubscriptionCost", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "", "type": "address"}], "name": "subscriptionExpiry", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "oracleStatus", "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "totalSubscriptions", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"internalType": "uint8", "name": "tier", "type": "uint8"}], "name": "purchaseSubscription", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "user", "type": "address"}, {"internalType": "uint8", "name": "tier", "type": "uint8"}], "name": "purchaseSubscriptionFor", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
]

RLC_ABI = [
    {"inputs": [{"internalType": "address", "name": "spender", "type": "address"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
]

# ═══════════ Web3 helpers ═══════════


def _get_w3() -> Web3:
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to Arbitrum RPC: {RPC_URL}")
    return w3


def _get_contracts(w3: Web3):
    oracle = w3.eth.contract(address=ORACLE_ADDRESS, abi=ORACLE_ABI)
    rlc = w3.eth.contract(address=RLC_ADDRESS, abi=RLC_ABI)
    return oracle, rlc


def _format_address(addr: str) -> str:
    raw = addr.strip()
    if not raw.startswith("0x"):
        raw = "0x" + raw
    return Web3.to_checksum_address(raw)


def _pretty(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _error(message: str) -> str:
    return json.dumps({"error": True, "message": message}, ensure_ascii=False, default=str)


# ═══════════ FastMCP server ═══════════

if os.environ.get("GLAMA_INSECURE_ALLOW_ANY_HOST") == "1":
    transport_security = {"enable_dns_rebinding_protection": False}
else:
    transport_security = {
        "enable_dns_rebinding_protection": True,
        "allowed_hosts": [
            "127.0.0.1:*", "localhost:*", "[::1]:*",
            "energy-arbitrage.io", "energy-arbitrage.io:*",
        ],
        "allowed_origins": [
            "http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
            "http://energy-arbitrage.io:*", "https://energy-arbitrage.io:*",
        ],
    }

mcp = FastMCP(
    "PJM-vs-MISO-Energy-Arbitrage-Oracle",
    instructions=(
        "Intel TDX attested energy oracle on Arbitrum One. "
        "Provides PJM vs MISO spatial arbitrage vector + price spread. "
        "Free: is_arbitrage_profitable / get_oracle_status / get_subscription_cost / check_subscription. "
        "Paid: get_telemetry (needs RLC subscription). "
        "Use build_subscription_tx to construct approve + purchase calldata. "
        "Public endpoint: https://energy-arbitrage.io/mcp"
    ),
    website_url=HOMEPAGE,
    icons=[Icon(
        src=f"{HOMEPAGE}/frame-preview.png",
        mimeType="image/png",
        sizes=["1200x630"],
    )],
    transport_security=transport_security,
)

# Set our own version (replaces SDK fallback version)
mcp._mcp_server.version = VERSION


def _readonly_annotations(title: str) -> dict:
    return {
        "title": title,
        "readOnlyHint": True,
        "idempotentHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    }


# ── Tool 1: oracle info ──

@mcp.tool(
    title="Oracle General Info",
    annotations=ToolAnnotations(**_readonly_annotations("Oracle General Info")),
)
def get_oracle_info() -> str:
    """PJM vs MISO Energy Arbitrage Oracle — general info: contract, network, TEE, pricing tiers. Starting point for any agent."""
    return _pretty({
        "name": "PJM vs MISO Energy Arbitrage Oracle",
        "description": "Spatial arbitrage vector + price spread between PJM West Hub and MISO Indiana Hub US wholesale electricity markets.",
        "contract_address": ORACLE_ADDRESS,
        "network": "Arbitrum One (chainId 42161)",
        "tee": "Intel TDX (iExec attested)",
        "update_interval": "60 minutes",
        "rlc_token": RLC_ADDRESS,
        "endpoint": PUBLIC_ENDPOINT,
        "homepage": HOMEPAGE,
        "explorer": f"https://arbiscan.io/address/{ORACLE_ADDRESS}",
        "version": VERSION,
        "subscription_tiers": [
            {"tier": tid, "name": t["name"], "duration": t["duration"],
             "target_price_usd": t["usd"],
             "note": "dynamic cost in RLC — call get_subscription_cost(tier)"}
            for tid, t in TIERS.items()
        ],
        "free_teaser": "is_arbitrage_profitable() — no subscription needed",
    })


# ── Tool 2: oracle status ──

@mcp.tool(
    title="Oracle Status",
    annotations=ToolAnnotations(**_readonly_annotations("Oracle Status")),
)
def get_oracle_status() -> str:
    """Check if the oracle is ACTIVE or in MAINTENANCE, and the number of active subscribers."""
    w3 = _get_w3()
    oracle, _ = _get_contracts(w3)
    status_code = oracle.functions.oracleStatus().call()
    total_subs = oracle.functions.totalSubscriptions().call()
    return _pretty({
        "status": "ACTIVE" if status_code == 0 else "MAINTENANCE",
        "status_code": status_code,
        "total_subscriptions": total_subs,
        "contract": ORACLE_ADDRESS,
    })


# ── Tool 3: check subscription ──

@mcp.tool(
    title="Check Subscription",
    annotations=ToolAnnotations(**_readonly_annotations("Check Subscription")),
)
def check_subscription(
    address: Annotated[str, Field(description="The agent's EVM address (0x...), e.g. 0x1234...")],
) -> str:
    """Check whether an EVM address has an active subscription. Returns expiry timestamp and human-readable info."""
    w3 = _get_w3()
    oracle, _ = _get_contracts(w3)
    try:
        addr = _format_address(address)
    except Exception as e:
        return _error(f"Invalid address: {e}")

    expiry_ts = oracle.functions.subscriptionExpiry(addr).call()
    now = int(time.time())

    if expiry_ts == 0 or expiry_ts < now:
        return _pretty({
            "address": addr,
            "has_subscription": False,
            "expiry_timestamp": expiry_ts,
            "next_step": "call build_subscription_tx(agent_address, tier) to purchase",
        })
    return _pretty({
        "address": addr,
        "has_subscription": True,
        "expiry_timestamp": expiry_ts,
        "expiry_human": time.ctime(expiry_ts),
        "remaining_seconds": expiry_ts - now,
    })


# ── Tool 4: subscription cost ──

@mcp.tool(
    title="Get Subscription Cost",
    annotations=ToolAnnotations(**_readonly_annotations("Get Subscription Cost")),
)
def get_subscription_cost(
    tier: Annotated[int, Field(description="Subscription tier: 0 = 1 day ($20), 1 = 3 days ($50), 2 = 7 days ($100)")],
) -> str:
    """Current subscription cost in RLC (dynamic, pegged to USD). Returns live cost from on-chain contract."""
    if tier not in TIERS:
        return _error(f"Invalid tier. Available: {list(TIERS.keys())}")
    w3 = _get_w3()
    oracle, _ = _get_contracts(w3)
    cost = oracle.functions.getSubscriptionCost(tier).call()
    tier_info = TIERS[tier]
    result = {
        "tier": tier,
        "name": tier_info["name"],
        "duration": tier_info["duration"],
        "target_price_usd": tier_info["usd"],
        "cost_rlc": f"{cost / 10**9:.2f}",
        "decimals": 9,
    }
    return _pretty(result)


# ── Tool 5: free teaser ──

@mcp.tool(
    title="Is Arbitrage Profitable",
    annotations=ToolAnnotations(**_readonly_annotations("Is Arbitrage Profitable")),
)
def is_arbitrage_profitable() -> str:
    """Free: is PJM vs MISO arbitrage profitable right now? No subscription needed."""
    w3 = _get_w3()
    oracle, _ = _get_contracts(w3)
    profitable = oracle.functions.isArbitrageProfitable().call()
    return _pretty({
        "arbitrage_profitable": profitable,
        "signal": "ARBITRAGE AVAILABLE" if profitable else "NEUTRAL / STALE",
        "note": "full vector + spread via get_telemetry (paid subscription)",
    })


# ── Tool 6: full telemetry ──

@mcp.tool(
    title="Get Telemetry",
    annotations=ToolAnnotations(**_readonly_annotations("Get Telemetry")),
)
def get_telemetry(
    subscriber_address: Annotated[str, Field(description="EVM address that has an active RLC subscription, e.g. 0x1234...")],
) -> str:
    """Full signal: arbitrageVector + priceSpread. Requires an active subscription. Executed as a view call: msg.sender = subscriber_address."""
    w3 = _get_w3()
    oracle, _ = _get_contracts(w3)
    try:
        addr = _format_address(subscriber_address)
    except Exception as e:
        return _error(f"Invalid address: {e}")

    try:
        timestamp, vector, spread, confidence = oracle.functions.getTelemetry().call({"from": addr})
    except Exception as e:
        msg = str(e)
        if "OracleUnderMaintenance" in msg:
            return _error("Oracle is in MAINTENANCE mode.")
        if "SubscriptionExpired" in msg:
            return _error("Subscription expired. Use build_subscription_tx().")
        if "MEVReadLocked" in msg:
            return _error("MEV lock: retry in the next block.")
        if "StaleTimestamp" in msg:
            return _error("Telemetry stale (>90 min); waiting for TEE update.")
        return _error(f"Error: {msg}")

    vector_desc = {1: "ROUTE TO MISO (MISO cheaper)", -1: "ROUTE TO PJM (PJM cheaper)", 0: "NEUTRAL (grids balanced)"}.get(vector, "UNKNOWN")
    return _pretty({
        "timestamp_slot": timestamp,
        "timestamp_human": time.ctime(timestamp) if timestamp else "N/A",
        "arbitrage_vector": vector,
        "vector_description": vector_desc,
        "price_spread_usd_per_mwh": f"{spread / 10**6:+.2f}",
        "confidence_score": confidence,
        "contract": ORACLE_ADDRESS,
    })


# ── Tool 7: build subscription tx ──

@mcp.tool(
    title="Build Subscription Transaction",
    annotations=ToolAnnotations(**_readonly_annotations("Build Subscription Transaction")),
)
def build_subscription_tx(
    agent_address: Annotated[str, Field(description="EVM address of the agent that will receive the subscription, e.g. 0x1234...")],
    tier: Annotated[int, Field(description="Subscription tier: 0 = 1 day ($20), 1 = 3 days ($50), 2 = 7 days ($100)")],
    sponsor_address: Annotated[Optional[str], Field(description="Optional EVM address of a sponsor who pays for the agent's subscription")] = None,
) -> str:
    """Build calldata to purchase a subscription: approve(RLC) + purchaseSubscription. The agent (or sponsor) signs and sends it themselves."""
    if tier not in TIERS:
        return _error(f"Invalid tier. Available: {list(TIERS.keys())}")
    w3 = _get_w3()
    oracle, rlc = _get_contracts(w3)
    try:
        agent_addr = _format_address(agent_address)
        sponsor_addr = _format_address(sponsor_address) if sponsor_address else None
    except Exception as e:
        return _error(f"Invalid address: {e}")

    cost = oracle.functions.getSubscriptionCost(tier).call()
    approve_data = rlc.encode_abi("approve", args=[ORACLE_ADDRESS, cost])

    if sponsor_addr:
        purchase_data = oracle.encode_abi("purchaseSubscriptionFor", args=[agent_addr, tier])
        payer = sponsor_addr
    else:
        purchase_data = oracle.encode_abi("purchaseSubscription", args=[tier])
        payer = agent_addr

    return _pretty({
        "chain_id": CHAIN_ID,
        "chain": "Arbitrum One",
        "tier": tier,
        "tier_name": TIERS[tier]["name"],
        "duration": TIERS[tier]["duration"],
        "cost_rlc": f"{cost / 10**9:.2f}",
        "payer": payer,
        "steps": [
            {"step": 1, "action": "approve RLC", "to": RLC_ADDRESS, "data": approve_data.hex()},
            {"step": 2, "action": "purchaseSubscription", "to": ORACLE_ADDRESS, "data": purchase_data.hex()},
        ],
        "how_to_send": "sign & send step 1, wait receipt, then sign & send step 2",
    })


# ── Tool 8: connection info ──

@mcp.tool(
    title="Connection Info",
    annotations=ToolAnnotations(**_readonly_annotations("Connection Info")),
)
def get_connection_info() -> str:
    """How to connect this oracle in Claude Desktop / Cursor / any MCP client, and the list of all available tools."""
    return _pretty({
        "protocol": "MCP (Model Context Protocol)",
        "server_name": "PJM-vs-MISO-Energy-Arbitrage-Oracle",
        "version": VERSION,
        "public_endpoint": PUBLIC_ENDPOINT,
        "homepage": HOMEPAGE,
        "catalogs": {
            "smithery": "https://smithery.ai/server/energy-arbitrage",
            "glama": "https://glama.ai/servers/energy-arbitrage",
            "pulsemcp": "https://pulsemcp.com/servers/energy-arbitrage",
        },
        "tools": [
            "get_oracle_info", "get_oracle_status",
            "check_subscription(address)", "get_subscription_cost(tier)",
            "is_arbitrage_profitable", "get_telemetry(subscriber_address)",
            "build_subscription_tx(agent_address, tier, sponsor_address?)",
            "get_sdk_template", "get_connection_info",
        ],
        "resources": ["oracle://status", "oracle://cost/{tier}", "oracle://subscription/{address}", "oracle://telemetry/{address}", "oracle://guide"],
        "prompts": ["oracle_arbitrage_check", "purchase_subscription_guide"],
        "sdk_note": "call get_sdk_template() to receive the full Python SDK code",
    })


# ── Tool 9: SDK template ──

try:
    from sdk_constant import SDK_TEMPLATE
except ImportError:
    SDK_TEMPLATE = None


def _sdk_from_disk() -> Optional[str]:
    here = Path(__file__).resolve().parent
    candidates = (here / "ai_agent_oracle_client.py", here.parent / "ai_agent_oracle_client.py")
    for candidate in candidates:
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        if "0x55d4E0EF665a747C43f8C67B8fd22A026c6aF326" in text and "priceSpread" in text:
            return text
    return None


def _sdk_header() -> str:
    return (
        "# ═════════════════════════════════════════════════════════════\n"
        "# PJM vs MISO Energy Arbitrage Oracle — Python SDK (AI agent)\n"
        "# Delivered via MCP tool get_sdk_template()\n"
        "# How to use:\n"
        "#   1. Save this text as ai_agent_oracle_client.py\n"
        "#   2. pip install web3 eth-account\n"
        "#   3. export AGENT_PRIVATE_KEY=0x...\n"
        "#   4. python ai_agent_oracle_client.py\n"
        "# ═════════════════════════════════════════════════════════════\n"
    )


@mcp.tool(
    title="Get SDK Template",
    annotations=ToolAnnotations(**_readonly_annotations("Get SDK Template")),
)
def get_sdk_template() -> str:
    """Get the FULL Python SDK code (ai_agent_oracle_client.py). Auto-cycle: check subscription → purchase (approve + purchase, RLC) → read signal. Suitable for non-MCP agents running on web3.py."""
    live = _sdk_from_disk()
    if live is not None:
        return _sdk_header() + live
    if SDK_TEMPLATE:
        return _sdk_header() + SDK_TEMPLATE
    return _error("SDK temporarily unavailable. Contact operator.")


# ═══════════ Resources ═══════════


@mcp.resource(
    uri="oracle://status",
    title="Oracle Live Status",
    description="Current oracle status (ACTIVE/MAINTENANCE) and subscriber count",
    mime_type="application/json",
)
def resource_status() -> str:
    try:
        w3 = _get_w3()
        oracle, _ = _get_contracts(w3)
        status_code = oracle.functions.oracleStatus().call()
        total_subs = oracle.functions.totalSubscriptions().call()
        return json.dumps({"status": "ACTIVE" if status_code == 0 else "MAINTENANCE", "total_subscriptions": total_subs})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource(
    uri="oracle://cost/{tier}",
    title="Subscription Cost",
    description="Current subscription cost in RLC for a given tier",
    mime_type="application/json",
)
def resource_cost(tier: int) -> str:
    try:
        w3 = _get_w3()
        oracle, _ = _get_contracts(w3)
        cost = oracle.functions.getSubscriptionCost(tier).call()
        return json.dumps({"tier": tier, "cost_rlc": str(cost), "cost_rlc_decimal": cost / 10**9})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource(
    uri="oracle://subscription/{address}",
    title="Subscription Status",
    description="Check if an EVM address has an active subscription",
    mime_type="application/json",
)
def resource_subscription(address: str) -> str:
    try:
        w3 = _get_w3()
        oracle, _ = _get_contracts(w3)
        addr = _format_address(address)
        expiry = oracle.functions.subscriptionExpiry(addr).call()
        return json.dumps({"address": addr, "expiry_timestamp": expiry, "has_subscription": expiry >= int(time.time())})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource(
    uri="oracle://telemetry/{address}",
    title="Oracle Telemetry",
    description="Full signal (vector + spread) for a subscriber",
    mime_type="application/json",
)
def resource_telemetry(address: str) -> str:
    try:
        w3 = _get_w3()
        oracle, _ = _get_contracts(w3)
        addr = _format_address(address)
        timestamp, vector, spread, confidence = oracle.functions.getTelemetry().call({"from": addr})
        return json.dumps({
            "timestamp_slot": timestamp,
            "arbitrage_vector": vector,
            "price_spread": str(spread),
            "confidence_score": confidence,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource(
    uri="oracle://guide",
    title="Oracle Usage Guide",
    description="Step-by-step guide for AI agents on using the oracle",
    mime_type="text/plain",
)

def resource_guide() -> str:
    return (
        "PJM vs MISO Energy Arbitrage Oracle — Agent Usage Guide\n"
        "====================================================\n"
        f"Contract: {ORACLE_ADDRESS} (Arbitrum One, chainId 42161)\n"
        f"RLC token: {RLC_ADDRESS}\n"
        f"Endpoint: {PUBLIC_ENDPOINT}\n"
        f"Website: {HOMEPAGE}\n\n"
        "What it does:\n"
        "Computes a real-time arbitrage vector between PJM West Hub and MISO\n"
        "Indiana Hub electricity prices inside an Intel TDX attested enclave.\n"
        "Updated every 60 minutes. Written on-chain.\n\n"
        "Free tools (no subscription needed):\n"
        "  is_arbitrage_profitable() — teaser: is there an arbitrage opportunity?\n"
        "  get_oracle_status() — is the oracle ACTIVE or in MAINTENANCE?\n"
        "  get_subscription_cost(tier) — current price in RLC (tier 0/1/2)\n"
        "  check_subscription(address) — expiry timestamp for an address\n"
        "  build_subscription_tx(wallet, tier) — calldata for approve + purchase\n"
        "  get_oracle_info() — contract, TEE, tiers, pricing\n"
        "  get_connection_info() — how to connect, list of all tools\n"
        "  get_sdk_template() — full Python SDK code\n\n"
        "Paid tool (requires active RLC subscription):\n"
        "  get_telemetry(wallet) — full signal: arbitrageVector + priceSpread\n\n"
        "Subscription steps:\n"
        "1. Ensure wallet has RLC + ETH (for gas) on Arbitrum One.\n"
        "2. Call build_subscription_tx(your_wallet, tier) → get approve + purchase calldata.\n"
        "3. Sign & send approve(RLC) → wait receipt → sign & send purchaseSubscription.\n"
        "4. Call get_telemetry(your_wallet) to read the signal.\n\n"
        "Pricing (dynamic, paid in RLC):\n"
        "  Tier 0: $20 / 24 hours  |  Tier 1: $50 / 72 hours  |  Tier 2: $100 / 7 days\n"
        "  Exact cost: call get_subscription_cost(tier) on-chain.\n\n"
        "Need RLC?\n"
        "  Buy on Coinbase/Kraken → withdraw to Arbitrum One.\n"
        "  RLC token address: 0xe649e6a1F2afc63ca268C2363691ceCAF75CF47C\n\n"
        "Need ETH for gas?\n"
        "  Bridge from Ethereum or withdraw from CEX directly to Arbitrum One.\n"
        "  ~$2-5 of ETH is enough for multiple subscriptions.\n\n"
        "Refund policy:\n"
        "  If the signal is stale (>90 min) or oracle is in MAINTENANCE,\n"
        "  call claimRefund() on the contract — your RLC is returned.\n"
        "  Funds are never locked forever.\n\n"
        "Security:\n"
        "  - Intel TDX attestation (remote verification)\n"
        "  - No private keys on the server — only view calls (eth_call)\n"
        "  - Spy blacklist/whitelist on-chain\n"
        "  - Open source: github.com/dornansgar390-hue/energy-oracle-group\n"
    )



# ═══════════ Prompts ═══════════


@mcp.prompt(
    name="oracle_arbitrage_check",
    title="Oracle Arbitrage Check",
    description="Guide the agent to check PJM vs MISO arbitrage and interpret the result.",
)
def prompt_arbitrage_check() -> list[dict]:
    return [{
        "role": "user",
        "content": "You have access to the PJM vs MISO Energy Arbitrage Oracle. "
        "To check the current signal: (1) call is_arbitrage_profitable for a free teaser; "
        "(2) call get_oracle_status to confirm ACTIVE; "
        "(3) call get_subscription_cost(tier=0) to see the current RLC price; "
        "(4) if the agent wallet has an active subscription, call get_telemetry(agent_address) "
        "for the full arbitrage vector and price spread; "
        "(5) otherwise use build_subscription_tx(agent_address, tier) to construct "
        "the approve + purchaseSubscription calldata. "
        f"The oracle contract is {ORACLE_ADDRESS} on Arbitrum One (chainId 42161)."
    }]


@mcp.prompt(
    name="purchase_subscription_guide",
    title="Purchase Subscription Guide",
    description="Step-by-step guide for an AI agent to purchase an RLC subscription.",
)
def prompt_purchase_guide() -> list[dict]:
    return [{
        "role": "user",
        "content": "To purchase a subscription for the PJM vs MISO Energy Arbitrage Oracle:\n\n"
        f"1. Ensure your wallet has RLC tokens and a small amount of ETH (for gas) on Arbitrum One (chainId 42161).\n"
        f"2. Call get_subscription_cost(tier) to see the dynamic RLC price (try tier=0 for 24h).\n"
        f"3. Call build_subscription_tx(your_wallet_address, tier) to get calldata for:\n"
        f"   - Step 1: approve RLC transfer to the oracle contract ({ORACLE_ADDRESS})\n"
        f"   - Step 2: purchaseSubscription(tier)\n"
        f"4. Sign and send both transactions.\n"
        f"5. Wait for confirmation, then call check_subscription(your_wallet_address) to verify.\n"
        f"6. Call get_telemetry(your_wallet_address) to read the full arbitrage signal.\n\n"
        "The oracle is powered by Intel TDX attested enclaves and updated every 60 minutes."
    }]


# ═══════════ Local run ═══════════

if __name__ == "__main__":
    print(f"⚡ {mcp.name} v{VERSION} starting at http://127.0.0.1:8000/mcp")
    print(f"   Contract: {ORACLE_ADDRESS} | Arbitrum One | Intel TDX")
    mcp.run(transport="streamable-http")
