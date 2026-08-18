// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IFlexibleEnergyOracle {
    enum OracleStatus { ACTIVE, MAINTENANCE }
    enum SpyDetectionStatus { None, Suspicious, ConfirmedSpy }

    struct Telemetry {
        uint256 timestampSlot;
        int256 pjm;
        int256 miso;
        int256 priceSpread;
        int8 arbitrageVector;
        uint256 confidenceScore;
        uint256 recordedBlock;
    }

    error UnauthorizedHub();
    error UnauthorizedApp();
    error StaleTimestamp();
    error SubscriptionExpired();
    error MEVReadLocked();
    error InvalidTier();
    error OracleUnderMaintenance();
    error AddressWhitelisted();
    error InsufficientRefundBalance();
    error NoRefundAvailable();

    event TelemetryUpdated(uint256 indexed timestampSlot, int256 pjm, int256 miso, int256 priceSpread, int8 arbitrageVector, uint256 confidenceScore, uint256 rlcPriceUsd);
    event SubscriptionPurchased(address indexed user, uint8 tier, uint256 expiry, uint256 costPaid);
    event OracleStatusChanged(OracleStatus indexed newStatus);
    event SpyBlacklisted(address indexed spy, bool isBlacklisted);
    event WhitelistUpdated(address indexed user, bool isWhitelisted);
    event RefundClaimed(address indexed user, uint256 refundAmount);
    event RlcPriceUpdated(uint256 oldPrice, uint256 newPrice);
    event SpyStatusUpdated(address indexed user, SpyDetectionStatus indexed status);

    function purchaseSubscription(uint8 tier) external;
    function purchaseSubscriptionFor(address user, uint8 tier) external;
    function isArbitrageProfitable() external view returns (bool);
    function getTelemetry() external view returns (uint256 timestampSlot, int8 arbitrageVector, uint256 confidenceScore);
    function getDisclaimer() external pure returns (string memory);
    function setOracleStatus(OracleStatus _status) external;
    function setBlacklisted(address spy, bool _isBlacklisted) external;
    function setWhitelisted(address user, bool _isWhitelisted) external;
    function resetSpyDetectionStatus(address user) external;
    function totalSubscriptions() external view returns (uint256);
    function claimRefund() external;
    function getSubscriptionCost(uint8 tier) external view returns (uint256);
}