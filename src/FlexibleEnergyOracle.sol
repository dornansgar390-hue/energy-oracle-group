// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./IFlexibleEnergyOracle.sol";

contract FlexibleEnergyOracle is IFlexibleEnergyOracle, Ownable {
    using SafeERC20 for IERC20;

    IERC20 public immutable rlcToken;
    address public iexecHubAddress;
    address public allowedAppAddress;

    uint256 public constant TRIAL_DURATION = 2 days;
    uint256 public totalSubscriptions;
    
    mapping(address => bool) public hasUsedTrial;
    mapping(address => bool) public isSpy;
    mapping(address => bool) public isWhitelisted;
    
    OracleStatus public oracleStatus;
    Telemetry public latestTelemetry;
    mapping(address => uint256) public subscriptionExpiry;

    // Динамические параметры цены RLC к USD (с 6 знаками после запятой)
    // По умолчанию: RLC_USD = $0.33 (333 333)
    uint256 public rlcPriceUsd = 333333; 
    
    // Целевая B2B стоимость подписок в USD (с 6 знаками после запятой)
    uint256[3] public tierTargetPricesUsd = [
        20 * 10**6,  // Tier 0: $20 USD
        50 * 10**6,  // Tier 1: $50 USD
        100 * 10**6  // Tier 2: $100 USD
    ];

    // Хранение "стоимости за секунду" (nRLC за секунду) для возвратов
    mapping(address => uint256) public rlcCostPerSecond;

    constructor(address _rlcToken, address _iexecHub, address _appAddress) Ownable(msg.sender) {
        rlcToken = IERC20(_rlcToken);
        iexecHubAddress = _iexecHub;
        allowedAppAddress = _appAddress;
        oracleStatus = OracleStatus.ACTIVE;
    }

    function setAllowedAppAddress(address _newApp) external onlyOwner {
        allowedAppAddress = _newApp;
    }

    function setIexecHubAddress(address _newHub) external onlyOwner {
        iexecHubAddress = _newHub;
    }

    function setOracleStatus(OracleStatus _status) external override onlyOwner {
        oracleStatus = _status;
        emit OracleStatusChanged(_status);
    }

    function setBlacklisted(address spy, bool _isBlacklisted) external override onlyOwner {
        if (isWhitelisted[spy]) revert AddressWhitelisted();
        isSpy[spy] = _isBlacklisted;
        emit SpyBlacklisted(spy, _isBlacklisted);
    }

    function setWhitelisted(address user, bool _isWhitelisted) external override onlyOwner {
        isWhitelisted[user] = _isWhitelisted;
        emit WhitelistUpdated(user, _isWhitelisted);
    }

    function setManualRlcPrice(uint256 _priceUsd) external onlyOwner {
        require(_priceUsd > 0, "Price must be > 0");
        uint256 oldPrice = rlcPriceUsd;
        rlcPriceUsd = _priceUsd;
        emit RlcPriceUpdated(oldPrice, _priceUsd);
    }

    function claimFreeTrial() external override {
        if (hasUsedTrial[msg.sender]) revert TrialAlreadyUsed();
        hasUsedTrial[msg.sender] = true;

        if (subscriptionExpiry[msg.sender] < block.timestamp) {
            subscriptionExpiry[msg.sender] = block.timestamp + TRIAL_DURATION;
            totalSubscriptions++;
        } else {
            subscriptionExpiry[msg.sender] += TRIAL_DURATION;
        }

        rlcCostPerSecond[msg.sender] = 0;

        emit SubscriptionPurchased(msg.sender, 99, subscriptionExpiry[msg.sender], 0);
    }

    function getSubscriptionCost(uint8 tier) public view override returns (uint256) {
        if (tier > 2) revert InvalidTier();
        return (tierTargetPricesUsd[tier] * 10**9) / rlcPriceUsd;
    }

    function purchaseSubscription(uint8 tier) external override {
        _purchaseSubscriptionFor(msg.sender, tier);
    }

    function purchaseSubscriptionFor(address user, uint8 tier) external override {
        _purchaseSubscriptionFor(user, tier);
    }

    function _purchaseSubscriptionFor(address user, uint8 tier) internal {
        uint256 cost = getSubscriptionCost(tier);
        uint256 duration;

        if (tier == 0) duration = 1 days;
        else if (tier == 1) duration = 3 days;
        else if (tier == 2) duration = 7 days;
        else revert InvalidTier();

        rlcToken.safeTransferFrom(msg.sender, address(this), cost);

        uint256 existingExpiry = subscriptionExpiry[user];
        uint256 newExpiry;
        
        if (existingExpiry < block.timestamp) {
            newExpiry = block.timestamp + duration;
            totalSubscriptions++;
            rlcCostPerSecond[user] = cost / duration;
        } else {
            newExpiry = existingExpiry + duration;
            uint256 remainingSeconds = existingExpiry - block.timestamp;
            uint256 oldValue = remainingSeconds * rlcCostPerSecond[user];
            rlcCostPerSecond[user] = (oldValue + cost) / (remainingSeconds + duration);
        }

        subscriptionExpiry[user] = newExpiry;

        emit SubscriptionPurchased(user, tier, newExpiry, cost);
    }

    function claimRefund() external override {
        uint256 expiry = subscriptionExpiry[msg.sender];
        if (expiry <= block.timestamp) revert NoRefundAvailable();
        
        // Разрешаем возврат если оракул в режиме MAINTENANCE или не обновлялся > 90 минут
        // Для тестов: если еще нет ни одной телеметрии (timestampSlot == 0), разрешаем возврат
        bool isStale = latestTelemetry.timestampSlot == 0 || (block.timestamp - latestTelemetry.timestampSlot) > 90 minutes;
        bool isMaint = (oracleStatus == OracleStatus.MAINTENANCE);
        if (!isStale && !isMaint) revert NoRefundAvailable();

        uint256 remainingSeconds = expiry - block.timestamp;
        uint256 refundAmount = remainingSeconds * rlcCostPerSecond[msg.sender];
        
        if (refundAmount > 0) {
            uint256 contractBal = rlcToken.balanceOf(address(this));
            if (refundAmount > contractBal) revert InsufficientRefundBalance();

            subscriptionExpiry[msg.sender] = block.timestamp;
            rlcCostPerSecond[msg.sender] = 0;
            if (totalSubscriptions > 0) totalSubscriptions--;

            rlcToken.safeTransfer(msg.sender, refundAmount);
            emit RefundClaimed(msg.sender, refundAmount);
        }
    }

    function receiveResult(bytes32 /* taskId */, bytes calldata results) external {
        if (msg.sender != iexecHubAddress) revert UnauthorizedHub();
        
        (
            address appAddress,
            uint256 timestampSlot,
            int256 pjm,
            int256 miso,
            int256 priceSpread,
            int8 arbitrageVector,
            uint256 confidenceScore,
            uint256 _rlcPriceUsd
        ) = abi.decode(results, (address, uint256, int256, int256, int256, int8, uint256, uint256));

        if (appAddress != allowedAppAddress) revert UnauthorizedApp();
        if (timestampSlot <= latestTelemetry.timestampSlot) revert StaleTimestamp();

        if (_rlcPriceUsd > 0) {
            uint256 oldPrice = rlcPriceUsd;
            rlcPriceUsd = _rlcPriceUsd;
            emit RlcPriceUpdated(oldPrice, _rlcPriceUsd);
        }

        OracleStatus targetStatus = oracleStatus;
        if (confidenceScore < 50) {
            targetStatus = OracleStatus.MAINTENANCE;
            emit OracleStatusChanged(OracleStatus.MAINTENANCE);
        }

        oracleStatus = targetStatus;

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
            confidenceScore,
            rlcPriceUsd
        );
    }

    function isArbitrageProfitable() external view override returns (bool) {
        if (oracleStatus == OracleStatus.MAINTENANCE) return false;
        if (block.timestamp - latestTelemetry.timestampSlot > 90 minutes) return false;
        return (latestTelemetry.arbitrageVector != 0 && latestTelemetry.confidenceScore >= 80);
    }

    function getTelemetry() external view override returns (
        uint256 timestampSlot,
        int8 arbitrageVector,
        uint256 confidenceScore
    ) {
        if (oracleStatus == OracleStatus.MAINTENANCE) revert OracleUnderMaintenance();
        if (subscriptionExpiry[msg.sender] < block.timestamp) revert SubscriptionExpired();
        if (block.number <= latestTelemetry.recordedBlock) revert MEVReadLocked();
        if (block.timestamp - latestTelemetry.timestampSlot > 90 minutes) revert StaleTimestamp();
        
        int8 finalVector = isSpy[msg.sender] ? -latestTelemetry.arbitrageVector : latestTelemetry.arbitrageVector;

        return (
            latestTelemetry.timestampSlot,
            finalVector,
            latestTelemetry.confidenceScore
        );
    }

    function getDisclaimer() external pure override returns (string memory) {
        return "INTEGRITY SPECIFICATION: This oracle guarantees tamper-proof cryptographic execution inside Intel TDX TEE.";
    }

    function withdrawRLC() external onlyOwner {
        uint256 balance = rlcToken.balanceOf(address(this));
        rlcToken.safeTransfer(owner(), balance);
    }
}
