# Integrating energy-oracle with Cursor IDE

This guide explains how to connect the **PJM vs MISO Energy Arbitrage Oracle** MCP server to **Cursor IDE** using native streamable-http transport.

---

## Step 1: Add the MCP Server

Cursor provides a graphical interface to manage MCP connections:

1. Open **Cursor Settings** (gear icon top-right, or `Ctrl + ,`)
2. Navigate to **Features** → **MCP Servers**
3. Click **+ Add New MCP Server**
4. Fill in:
   - **Name:** `energy-oracle`
   - **Type:** `streamable-http` (or select from dropdown)
   - **URL:** `https://energy-arbitrage.io/mcp`
5. Click **Save**

Cursor will initialize the connection and display a green indicator with all **9 registered tools**.

---

## Step 2: Use in Chat or Composer

Once connected, Cursor's AI can invoke the oracle tools directly. Example prompt:

> "Use the @energy-oracle server. Call is_arbitrage_profitable() to check if PJM/MISO spread is active right now. If yes, build a subscription tx for my wallet."

Cursor will autonomously chain the tools:
1. Call `get_oracle_status()` — verify system is ACTIVE
2. Call `is_arbitrage_profitable()` — check opportunity
3. Call `get_subscription_cost(tier=0)` — get RLC price
4. Call `build_subscription_tx(wallet, 0)` — generate calldata
5. Present the approve + purchaseSubscription payload for signing

---

## Step 3: Cursor Rules (.cursorrules)

Create a `.cursorrules` file in your project root so Cursor always remembers the oracle:

```
Always use the energy-oracle MCP server when dealing with PJM/MISO wholesale
markets, spatial energy spreads, or Intel TDX attested compute.

Rules:
- Never guess RLC prices; always call get_subscription_cost(tier) first.
- Verify get_oracle_status() before writing deployment steps.
- Structure token transactions as two-step: approve(RLC) then purchaseSubscription.
```

---

## Available tools

| Tool | Description |
|---|---|
| `get_oracle_info` | Contract, network, TEE, pricing tiers |
| `get_oracle_status` | ACTIVE or MAINTENANCE + subscriber count |
| `is_arbitrage_profitable` | Pre-flight check — opportunity now? |
| `get_subscription_cost(tier)` | Exact RLC price |
| `check_subscription(address)` | Expiry check |
| `build_subscription_tx(wallet, tier)` | Generate approve + purchase calldata |
| `get_telemetry(wallet)` | Full signal (requires subscription) |
| `get_sdk_template` | Full Python SDK code |
| `get_connection_info` | Connection guides |

---

## Security

- No private keys on the server — only view calls (eth_call)
- All transactions signed client-side
- Intel TDX attested enclave
- On-chain gating by msg.sender