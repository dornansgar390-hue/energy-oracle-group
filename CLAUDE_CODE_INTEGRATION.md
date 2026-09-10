# Integrating energy-oracle with Claude Code

This guide explains how to connect the **PJM vs MISO Energy Arbitrage Oracle** MCP server to **Claude Code** (Anthropic's terminal-native CLI agent) using standard MCP configuration.

---

## Step 1: Configure MCP in Claude Code

Claude Code reads MCP servers from `~/.claude.json` (or `$CLAUDE_CONFIG_DIR/claude.json`). Add the oracle:

```bash
claude mcp add energy-oracle --transport http https://energy-arbitrage.io/mcp
```

Or edit the config file manually:

```json
{
  "mcpServers": {
    "energy-oracle": {
      "url": "https://energy-arbitrage.io/mcp",
      "transport": "streamable-http"
    }
  }
}
```

---

## Step 2: Use the Agent Workflow

Once connected, Claude Code can autonomously:

1. Call `get_oracle_info()` — map contract addresses
2. Call `is_arbitrage_profitable()` — check if PJM/MISO spread is active
3. Call `get_subscription_cost(tier)` — get exact RLC price
4. Call `build_subscription_tx(wallet, tier)` — generate calldata
5. If you hold private keys: sign approve(RLC) + purchaseSubscription
6. Call `get_telemetry(wallet)` — read the full signal

---

## Step 3: Example Prompt for Claude Code

```
Analyze the current PJM vs MISO energy arbitrage opportunity using the
energy-oracle MCP server:
1. Check get_oracle_status() — is the oracle ACTIVE?
2. Call is_arbitrage_profitable() — is there a profitable spread now?
3. If profitable, call get_subscription_cost(tier=0) for the price.
4. Then call build_subscription_tx([my_wallet], 0) to get the calldata.
5. Present the two-step transaction (approve + purchase) for signing.
```

---

## Security Notes

- The server never holds private keys — all transactions are signed client-side
- Only view calls (`eth_call`) are executed server-side
- Intel TDX attested enclave guarantees computation integrity
- Refund available via `claimRefund()` if signal goes stale (>90 min)