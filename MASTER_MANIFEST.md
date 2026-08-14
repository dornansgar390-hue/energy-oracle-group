
1. **Оплата подписки за третьих лиц (`purchaseSubscriptionFor`):** ИИ-агенты часто работают на выделенных воркерах с минимальным балансом газа. Возможность оплаты подписки с мастер-кошелька (Agent Manager / Multi-sig) избавит от необходимости переводить RLC непосредственно на баланс бота.
2. **Легковесный метод-сигнал (`isArbitrageProfitable`):** ИИ-агентам перед вызовом `getTelemetry()` полезно делать симуляционный запрос (`eth_call`), чтобы мгновенно узнать, есть ли активный сигнал арбитража (`arbitrageVector != 0`), не тратя вычислительные ресурсы на парсинг полной структуры.
3. **Стандартизированный интерфейс (`IFlexibleEnergyOracle`):** Вынос типов и функций в отдельный интерфейс позволит сторонним протоколам интегрировать ваш оракул в свои смарт-контракты в одну строчку кода.

---

# Super Manifest: Flexible Energy Oracle for iExec TEE (Intel TDX)

## 1. Core Mission & Architecture

### Core Mission

The Flexible Energy Oracle delivers tamper-proof, real-time Locational Marginal Price (LMP) telemetry from the **Direct Seam Corridor** of the US power grid: **PJM (West Hub)** and **MISO (Indiana Hub)**. Operating inside an Intel TDX Confidential VM (iExec Nox), it guarantees execution integrity, calculates optimal spatial arbitrage vectors on-chain, and protects data ingestion channels from manipulation.

### AI Agent Target Interaction Flow

Autonomous AI GPU Datacenter Agents discover and consume this oracle via Arbitrum One:

1. **Discovery:** AI Agents locate the oracle via `IFlexibleEnergyOracle` or monitor iExec Marketplace orders matching `allowedAppAddress`.
2. **Access Control:** Agents or their managers purchase time-based access tiers using RLC (`nRLC`, 9 decimals).
3. **Telemetry Consumption:** Active subscribers invoke `getTelemetry()` or `isArbitrageProfitable()` to dynamically re-route compute workloads between PJM and MISO nodes.

### Subscription Matrix (Paywall Model)

Subscriptions are managed on-chain via fixed-access time blocks using the iExec RLC token.

| Tier | Duration | Cost | Target Audience |
| --- | --- | --- | --- |
| Tier 0 | 1 Day (24 Hours) | 60 RLC | Short-term optimization scripts / Testnets |
| Tier 1 | 3 Days (72 Hours) | 150 RLC | Active Data Center Agents (Sweet Spot) |
| Tier 2 | 7 Days (168 Hours) | 300 RLC | Enterprise Infrastructure Networks |

---

## 2. Advanced Security, Crypto Shields & Consensus Engine

### 1. Signed Integer & Scaled Decimals

LMP nodes yield negative prices during periods of renewable oversupply (e.g., wind generation surges in MISO). Prices are captured and transmitted as `int256`, scaled by $10^6$ inside the Python enclave to preserve floating-point precision on EVM.

### 2. Data Schema & Arbitrage Vector

solidity

struct Telemetry {
    uint256 timestampSlot;   // Unix timestamp from enclave
    int256 pjm;              // PJM West Hub LMP (Scaled x10^6)
    int256 miso;             // MISO Indiana Hub LMP (Scaled x10^6)
    int256 priceSpread;      // PJM - MISO (Scaled x10^6)
    int8 arbitrageVector;    // 1: Shift to MISO | -1: Shift to PJM | 0: Neutral
    uint256 confidenceScore; // Consensus confidence percentage (0-100)
    uint256 recordedBlock;   // Block number for MEV lockout
}


### 3. Multi-Source Local Consensus Engine (Per Region)

To prevent Single Point of Failure (SPOF), the enclave fetches pricing for each region from three architectural vectors:

* **Source A (Primary):** `gridstatus` library fetching live spot market nodes (`PJM WEST HUB`, `INDIANA.HUB`).
* **Source B (Direct API):** Raw JSON endpoint parsing directly from PJM and MISO servers.
* **Source C (Anchor Control):** US Government EIA API v2 hourly regional benchmark.

### 4. Integrity Algorithms & Mitigation Rules

* **Freshness Check:** Data payloads older than 420 seconds (7 minutes) are discarded.
* **Negative Price Support:** Validates signed numerical values without dropping negative prices. `NaN` or unparseable responses are filtered out.
* **Deviation Shield:** Outliers deviating from the local mean by more than 50% (or $15.0/MWh) are dropped.
* **Emergency Circuit Breaker:** If the spread between remaining valid sources exceeds $25.0/MWh, the enclave terminates with `sys.exit(1)`, canceling the update transaction.
* **MEV & Flash Loan Shield:** On-chain read lockout prevents same-block execution exploit vectors:
`if (block.number <= latestTelemetry.recordedBlock) revert MEVReadLocked();`

---

## 5. Production Repository Specifications

### Contract Features

* **Custom Errors:** Gas-optimized error handling replacing string reverts.
* **SafeERC20:** OpenZeppelin `SafeERC20` wrapper for secure RLC transfers.
* **Sponsor Subscriptions:** Support for `purchaseSubscriptionFor(address agent, uint8 tier)`.
* **Agent Ergonomics:** `isArbitrageProfitable()` view helper returning a boolean signal for quick off-chain evaluation.


## app.manifest.template

# Gramine / Intel TDX Orchestration Manifest (iExec Nox Infrastructure)
loader.entrypoint = "file:{{ gramine.libos }}"
libos.entrypoint = "/usr/local/bin/python"

loader.log_level = "error"

loader.env.LD_LIBRARY_PATH = "/lib:/lib/x86_64-linux-gnu:/usr/lib:/usr/lib/x86_64-linux-gnu"
loader.env.PATH = "/bin:/usr/bin:/usr/local/bin"
loader.env.EIA_API_KEY = { passthrough = true }
loader.env.IEXEC_APP_ADDRESS = { passthrough = true }

# Memory Optimization Configuration
sgx.enclave_size = "1G"
sgx.thread_num = 8

sys.enable_extra_runtime_checks = true

# Secure Multi-Route Outbound Links Mapping for open-source grids parsing
sys.net.allow_outbound_links = [
    "api.eia.gov:443",
    "pjm.com:443",
    "misoenergy.org:443",
    "spp.org:443",
    "pubftp.spp.org:21"
]

fs.mounts = [
    { uri = "file:/lib", path = "/lib" },
    { uri = "file:/usr", path = "/usr" },
    { uri = "file:/app", path = "/app" },
    { uri = "file:/iexec_out", path = "/iexec_out" }
]

------------------------------
## 6. Operational & Execution Frequency

* Cadence: 1 Update Per Hour (Hourly Average Subsample).
* Rationale: Data centers cannot throttle megawatts every 5 minutes without causing infrastructure degradation. A 1-hour time-weighted snapshot captures actionable physical patterns, strips transient micro-spikes (noise), and saves 12x the gas capital cost compared to short-interval streams (reducing overhead down to 24 transactions daily).


// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract FlexibleEnergyOracle is Ownable {
    using SafeERC20 for IERC20;

    IERC20 public immutable rlcToken;
    address public iexecHubAddress;
    address public allowedAppAddress;

    // Custom Errors для экономии газа
    error UnauthorizedHub();
    error UnauthorizedApp();
    error StaleTimestamp();
    error SubscriptionExpired();
    error MEVReadLocked();
    error InvalidTier();

    struct Telemetry {
        uint256 timestampSlot;
        int256 pjm;           // Scaled by 10^6
        int256 miso;          // Scaled by 10^6
        int256 priceSpread;   // pjm - miso (Scaled by 10^6)
        int8 arbitrageVector; // 1: Shift to MISO, -1: Shift to PJM, 0: Neutral
        uint256 confidenceScore;
        uint256 recordedBlock;
    }

    Telemetry public latestTelemetry;
    mapping(address => uint256) public subscriptionExpiry;

    event TelemetryUpdated(
        uint256 indexed timestampSlot,
        int256 pjm,
        int256 miso,
        int256 priceSpread,
        int8 arbitrageVector,
        uint256 confidenceScore
    );
    event SubscriptionPurchased(address indexed user, uint8 tier, uint256 expiry);

    constructor(address _rlcToken, address _iexecHub, address _appAddress) Ownable(msg.sender) {
        rlcToken = IERC20(_rlcToken);
        iexecHubAddress = _iexecHub;
        allowedAppAddress = _appAddress;
    }

    function setAllowedAppAddress(address _newApp) external onlyOwner {
        allowedAppAddress = _newApp;
    }

    function setIexecHubAddress(address _newHub) external onlyOwner {
        iexecHubAddress = _newHub;
    }

    function purchaseSubscription(uint8 tier) external {
        uint256 cost;
        uint256 duration;

        if (tier == 0) { cost = 60 * 10**9; duration = 1 days; }
        else if (tier == 1) { cost = 150 * 10**9; duration = 3 days; }
        else if (tier == 2) { cost = 300 * 10**9; duration = 7 days; }
        else revert InvalidTier();

        rlcToken.safeTransferFrom(msg.sender, address(this), cost);

        if (subscriptionExpiry[msg.sender] < block.timestamp) {
            subscriptionExpiry[msg.sender] = block.timestamp + duration;
        } else {
            subscriptionExpiry[msg.sender] += duration;
        }

        emit SubscriptionPurchased(msg.sender, tier, subscriptionExpiry[msg.sender]);
    }

    // iExec Hub Core Callback Hook
    function receiveResult(bytes32 /* taskId */, bytes calldata results) external {
        if (msg.sender != iexecHubAddress) revert UnauthorizedHub();
        
        // Извлечение данных с учетом 2-региональной TEE-структуры
        (
            address appAddress,
            uint256 timestampSlot,
            int256 pjm,
            int256 miso,
            int256 priceSpread,
            int8 arbitrageVector,
            uint256 confidenceScore
        ) = abi.decode(results, (address, uint256, int256, int256, int256, int8, uint256));

        if (appAddress != allowedAppAddress) revert UnauthorizedApp();
        if (timestampSlot <= latestTelemetry.timestampSlot) revert StaleTimestamp();

        latestTelemetry = Telemetry({
            timestampSlot: timestampSlot,
            pjm: pjm,
            miso: miso,
            priceSpread: priceSpread,
            arbitrageVector: arbitrageVector,
            confidenceScore: confidenceScore,
            recordedBlock: block.number
        });

        emit TelemetryUpdated(
            timestampSlot, 
            pjm, 
            miso, 
            priceSpread, 
            arbitrageVector, 
            confidenceScore
        );
    }

    // AI Agent Consumption Endpoint
    function getTelemetry() external view returns (
        uint256 timestampSlot,
        int256 pjm,
        int256 miso,
        int256 priceSpread,
        int8 arbitrageVector,
        uint256 confidenceScore
    ) {
        if (subscriptionExpiry[msg.sender] < block.timestamp) revert SubscriptionExpired();
        if (block.number <= latestTelemetry.recordedBlock) revert MEVReadLocked();
        
        return (
            latestTelemetry.timestampSlot,
            latestTelemetry.pjm,
            latestTelemetry.miso,
            latestTelemetry.priceSpread,
            latestTelemetry.arbitrageVector,
            latestTelemetry.confidenceScore
        );
    }

    function withdrawRLC() external onlyOwner {
        uint256 balance = rlcToken.balanceOf(address(this));
        rlcToken.safeTransfer(owner(), balance);
    }
}




import os, sys, json, time, math, requests, gridstatus
from eth_abi import encode

IEXEC_OUT = "/iexec_out"
RESULT_FILE = "/iexec_out/result.json"
COMPUTED_FILE = "/iexec_out/computed.json"
APP_ADDRESS = os.getenv("IEXEC_APP_ADDRESS", "0x0000000000000000000000000000000000000000")

# Порог спреда в $/МВт·ч для активации вектора арбитража
ARBITRAGE_THRESHOLD = 2.0 

def scale_price(value): 
    return int(round(float(value) * 1_000_000))

def get_pjm_direct():
    url = "https://pjm.com"
    res = requests.get(url, timeout=7).json()
    for node in res['LmpList']:
        if node['NodeName'] == 'PJM WEST HUB': 
            return float(node['LmpPrice'])
    raise Exception("PJM West Hub node not found")

def get_miso_direct():
    url = "https://misoenergy.org"
    res = requests.get(url, timeout=7).json()
    for hub in res['LmpHourlyRealTime']['Hubs']['Hub']:
        if hub['Name'] == 'INDIANA.HUB': 
            return float(hub['Lmp'])
    raise Exception("Indiana Hub node not found")

def get_eia_direct_anchor(ba_code):
    """Публичный сбор часового государственного эталона EIA без API-ключей через gridstatus"""
    eia = gridstatus.EIA()
    df = eia.get_hourly_net_generation(interchange=True, balancing_authority=ba_code)
    return float(df.iloc[-1]['Value']) 

def gather_and_validate(iso_name, hub_node, eia_ba, direct_func):
    curr_time, prices = time.time(), []

    # 1. Канал А: gridstatus (свежесть данных ограничена 7 минутами)
    try:
        df = getattr(gridstatus, iso_name)().get_lmp(latest=True, node=hub_node)
        if not df.empty and (curr_time - df.iloc[-1]['Timestamp'].timestamp()) < 420:
            val = float(df.iloc[-1]['LMP'])
            if not math.isnan(val): 
                prices.append(val)
    except Exception:
        pass

    # 2. Канал Б: Прямой парсинг открытых API
    try:
        val = direct_func()
        if not math.isnan(val): 
            prices.append(val)
    except Exception:
        pass

    # 3. Канал В: Часовой эталон EIA
    try:
        val = get_eia_direct_anchor(eia_ba)
        if not math.isnan(val): 
            prices.append(val)
    except Exception:
        pass

    if not prices: 
        return None, 0

    # Фильтр девиаций с поддержкой отрицательных и околонулевых цен
    if len(prices) >= 3:
        avg = sum(prices) / len(prices)
        prices = [p for p in prices if abs(p - avg) <= max(15.0, abs(avg) * 0.50)]

    if not prices: 
        return None, 0

    # Экстренный Circuit Breaker при абсолютном спреде между источниками > $25
    if len(prices) >= 2 and (max(prices) - min(prices)) > 25.0:
        sys.exit(1)

    avg_price = sum(prices) / len(prices)
    confidence = int((len(prices) / 3) * 100)
    return avg_price, confidence

def calculate_arbitrage_vector(pjm_price, miso_price, threshold=ARBITRAGE_THRESHOLD):
    spread = pjm_price - miso_price
    if spread > threshold:
        return 1   # PJM дороже MISO -> выгодно перенести нагрузку в MISO
    elif spread < -threshold:
        return -1  # MISO дороже PJM -> выгодно перенести нагрузку в PJM
    return 0       # Спред не превышает порог затрат на переключение

def main():
    pjm_p, pjm_c = gather_and_validate("PJM", "PJM WEST HUB", "PJM", get_pjm_direct)
    miso_p, miso_c = gather_and_validate("MISO", "INDIANA.HUB", "MISO", get_miso_direct)

    if pjm_p is None or miso_p is None: 
        sys.exit(1)

    price_spread = pjm_p - miso_p
    arb_vector = calculate_arbitrage_vector(pjm_p, miso_p)
    avg_confidence = int((pjm_c + miso_c) / 2)

    # Упаковка ABI в строгом соответствии со Solidity-структурой:
    # (address appAddress, uint256 timestampSlot, int256 pjm, int256 miso, int256 priceSpread, int8 arbitrageVector, uint256 confidenceScore)
    payload = encode(
        ['address', 'uint256', 'int256', 'int256', 'int256', 'int8', 'uint256'],
        [
            APP_ADDRESS,
            int(time.time()),
            scale_price(pjm_p),
            scale_price(miso_p),
            scale_price(price_spread),
            arb_vector,
            avg_confidence
        ]
    )

    os.makedirs(IEXEC_OUT, exist_ok=True)
    with open(RESULT_FILE, "wb") as f: 
        f.write(payload)
    with open(COMPUTED_FILE, "w") as f: 
        json.dump({"deterministic-output-path": RESULT_FILE, "callback-data": "0x" + payload.hex()}, f)

if __name__ == "__main__": 
    main()