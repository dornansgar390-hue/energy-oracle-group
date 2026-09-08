# Terms of Service — PJM vs MISO Energy Arbitrage Oracle

**Last updated:** September 2026

## 1. Service definition

The Service provides **derived analytical signals** (arbitrage vector + price spread) computed inside an Intel TDX attested enclave from publicly available US wholesale electricity market data. The Service does **NOT** provide, expose, or redistribute raw Locational Marginal Price (LMP) values, raw market data, or any database content of PJM, MISO, or any market operator.

The output is a proprietary computational index — a new work created by the oracle's analytical methodology.

## 2. Access and subscription

- Access to the full signal (`getTelemetry`) requires an **active paid subscription** purchased in RLC on Arbitrum One (chainId 42161).
- The free teaser (`isArbitrageProfitable`) is provided without a subscription for evaluation purposes only.
- Subscription purchase and expiry are enforced on-chain by the oracle smart contract at `0x55d4E0EF665a747C43f8C67B8fd22A026c6aF326`.
- Subscription pricing is dynamic (USD-pegged, paid in RLC) — exact cost available via `getSubscriptionCost(tier)`.

## 3. Permitted use

The signal is licensed solely for the **subscriber's own use**, including but not limited to:
- Optimizing own electricity consumption and operational costs;
- Load shifting and workload routing decisions for the subscriber's own compute infrastructure;
- Internal analytics and operational reporting.

## 4. Prohibited use

Without explicit prior written consent from the operator, you may NOT:

- **Reproduce, resell, redistribute, sublicense, or publicly rebroadcast** the signals, spread values, or any derived output, whether in whole or in part;
- **Combine the signal with other data** to reconstruct, infer, or approximate underlying LMP values or market data;
- **Provide access to third parties** (including sub-agents, affiliates, or API services) without purchasing a separate subscription on their behalf;
- **Use the signal to create a competing data product** or oracle service.

## 5. Compliance framework

The Service operates under the principle of **optimization of own consumption** as recognized by:
- **FERC Order 745** (Demand Response Compensation)
- **FERC Order 2222** (Distributed Energy Resource Participation)
- Relevant RTO/ISO tariff provisions

The Service provides a decision signal. It does not submit market orders, create fictitious demand, or engage in market manipulation. The subscriber bears responsibility for lawful use of the signal within their jurisdiction.

## 6. Intellectual property

- The **analytical methodology and composite index formula** constitute proprietary intellectual property protected under applicable trade secret and copyright laws.
- The **source code** is licensed separately under the MIT License (see `LICENSE`). This does not grant rights to the analytical data or signals produced by the software.
- All rights not expressly granted are reserved.

## 7. Disclaimer

THE SERVICE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL THE OPERATORS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY ARISING FROM THE USE OF THE SERVICE.

The Service provides an analytical index only. It is not financial, legal, or investment advice.

## 8. Contact

For licensing inquiries, bulk subscriptions, or commercial redistribution requests: refer to the repository owner.
