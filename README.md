# ⚡ PJM vs MISO Energy Arbitrage Oracle

**Real-time PJM/MISO spatial arbitrage signal, attested by Intel TDX, on Arbitrum One.**

## What it is
A confidential-compute oracle that continuously computes a derived analytical index
from public US wholesale electricity market data (PJM West Hub vs MISO Indiana Hub).
Written on-chain every 60 minutes.


## Key facts
| Item | Value |
|---|---|
| Contract | `0x55d4E0EF665a747C43f8C67B8fd22A026c6aF326` (Arbitrum One) |
| TEE | Intel TDX (iExec attested) |
| Update | every 60 minutes |
| Payment | RLC token |
| MCP endpoint | `https://energy-arbitrage.io/mcp` |
| x402 | `https://energy-arbitrage.io/.well-known/x402.json` |


## Available tools
| Tool | Description | Free/Paid |
|---|---|---|
| `is_arbitrage_profitable()` | free teaser | Free |
| `get_oracle_status()` | status | Free |
| `get_subscription_cost(tier)` | cost in RLC | Free |
| `check_subscription(address)` | expiry check | Free |
| `get_telemetry(subscriber)` | full signal | Paid |
| `build_subscription_tx(agent, tier)` | purchase calldata | Free |
| `get_sdk_template()` | full SDK code | Free |
| `get_oracle_info` | meta info: contract, network, tiers | Free |
| `get_connection_info` | client connection guide | Free |


## Pricing (USD-pegged, paid in RLC)
| Tier | Duration | USD | ~RLC |
|---|---|---|---|
| 0 | 24h | $20 | ~65 |
| 1 | 72h | $50 | ~161 |
| 2 | 7d | $100 | ~322 |

Exact cost: `getSubscriptionCost(tier)` on-chain.

## Compliance & data policy

This oracle provides **derived analytical signals** (arbitrage vector + price spread),
NOT raw market data. Full legal rationale: [`legal_and_compliance.md`](legal_and_compliance.md).
Access terms: [`TERMS.md`](TERMS.md).

- ✅ No raw LMP values are exposed or redistributed
- ✅ Access to the full signal requires a paid subscription (enforced on-chain by the smart contract)
- ✅ Output is a proprietary computational index, not a copy of market data
- ✅ Resale or redistribution of the signal to third parties is prohibited (see TERMS.md)
- ✅ The signal is intended for optimization of own consumption (FERC Order 745 / 2222)
- ✅ The analytical methodology is protected as proprietary intellectual property


## Buy access
1. Wallet needs RLC + ETH (gas) on Arbitrum One.
2. Call `build_subscription_tx(wallet, tier)` → get purchase calldata.
3. Sign & send, then call `get_telemetry(wallet)`.



## Architecture
[TEE cron] → [Oracle contract] ← eth_call ← [MCP server uvicorn] ← Caddy/HTTPS


## Security
- Intel TDX attestation
- On-chain gating by msg.sender
- Spy blacklist/whitelist
- No private keys server-side


## How to connect an AI agent (MCP)
Streamable HTTP transport.

Config for Claude/Cursor/any MCP client:
```json
{
  "mcpServers": {
    "energy-oracle": {
      "url": "https://energy-arbitrage.io/mcp"
    }
  }
}