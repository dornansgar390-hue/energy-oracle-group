// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/FlexibleEnergyOracle.sol";

contract MockRLC {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "Balance low");
        require(allowance[from][msg.sender] >= amount, "Allowance low");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Balance low");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

contract FlexibleEnergyOracleTest is Test {
    FlexibleEnergyOracle public oracle;
    MockRLC public rlc;

    address public owner = address(1);
    address public iexecHub = address(1);
    address public enclave = address(2);
    address public aiAgent = address(3);
    address public spy = address(4);

    uint256 public price = 150 * 10**9;

    function setUp() public {
        vm.prank(owner);
        rlc = new MockRLC();

        vm.prank(owner);
        oracle = new FlexibleEnergyOracle(address(rlc), iexecHub, enclave);

        rlc.mint(aiAgent, 1000 * 10**9);
        rlc.mint(spy, 1000 * 10**9);
    }

    function test_EnclaveCanUpdateTelemetry() public {
        bytes memory d = abi.encode(enclave, block.timestamp, int256(100), int256(150), int256(-50), int8(-1), uint256(100), uint256(333333));
        vm.prank(iexecHub);
        oracle.receiveResult(bytes32(0), d);
        assertTrue(oracle.isArbitrageProfitable());
    }

    function test_NonIexecHubCannotUpdateTelemetry() public {
        vm.prank(aiAgent);
        vm.expectRevert();
        oracle.receiveResult(bytes32(0), abi.encode(enclave, block.timestamp, 456, 123));
    }

    function test_AgentCannotReadWithoutSubscription() public {
        vm.prank(aiAgent);
        vm.expectRevert();
        oracle.getTelemetry();
    }

    function test_AgentCanClaimFreeTrial() public {
        vm.prank(aiAgent);
        oracle.claimFreeTrial();

        assertEq(oracle.subscriptionExpiry(aiAgent), block.timestamp + 48 hours);
        assertTrue(oracle.hasUsedTrial(aiAgent));
        assertEq(oracle.totalSubscriptions(), 1);

        vm.prank(aiAgent);
        (uint256 timestamp, int8 vector, ) = oracle.getTelemetry();
        assertEq(timestamp, 0);
        assertEq(vector, 0);
    }

    function test_AgentCanBuyAccess() public {
        uint256 cost = oracle.getSubscriptionCost(1);
        vm.startPrank(aiAgent);
        rlc.approve(address(oracle), cost);
        oracle.purchaseSubscription(1);
        vm.stopPrank();

        assertEq(oracle.subscriptionExpiry(aiAgent), block.timestamp + 3 days);
        assertEq(oracle.totalSubscriptions(), 1);
    }

    function test_SponsorCanBuyAccessForAgent() public {
        address sponsor = address(5);
        rlc.mint(sponsor, 1000 * 10**9);

        uint256 cost = oracle.getSubscriptionCost(1);
        vm.startPrank(sponsor);
        rlc.approve(address(oracle), cost);
        oracle.purchaseSubscriptionFor(aiAgent, 1);
        vm.stopPrank();

        assertEq(oracle.subscriptionExpiry(aiAgent), block.timestamp + 3 days);
        assertEq(oracle.totalSubscriptions(), 1);
    }

    function test_MaintenanceBlocksTelemetry() public {
        bytes memory d = abi.encode(enclave, block.timestamp, int256(100), int256(80), int256(20), int8(1), uint256(100), uint256(333333));
        vm.prank(iexecHub);
        oracle.receiveResult(bytes32(0), d);

        vm.prank(owner);
        oracle.setOracleStatus(IFlexibleEnergyOracle.OracleStatus.MAINTENANCE);

        vm.prank(aiAgent);
        vm.expectRevert(IFlexibleEnergyOracle.OracleUnderMaintenance.selector);
        oracle.getTelemetry();

        assertFalse(oracle.isArbitrageProfitable());
    }

    function test_SpyGetsPoisonedSignals() public {
        bytes memory d = abi.encode(enclave, block.timestamp, int256(100), int256(80), int256(20), int8(1), uint256(100), uint256(333333));
        vm.prank(iexecHub);
        oracle.receiveResult(bytes32(0), d);

        uint256 cost = oracle.getSubscriptionCost(1);
        vm.startPrank(aiAgent);
        rlc.approve(address(oracle), cost);
        oracle.purchaseSubscription(1);
        vm.stopPrank();

        vm.startPrank(spy);
        rlc.approve(address(oracle), cost);
        oracle.purchaseSubscription(1);
        vm.stopPrank();

        vm.prank(owner);
        oracle.setBlacklisted(spy, true);

        vm.roll(block.number + 1);

        vm.prank(aiAgent);
        (, int8 normalVector, ) = oracle.getTelemetry();
        assertEq(normalVector, 1);

        vm.prank(spy);
        (, int8 spyVector, ) = oracle.getTelemetry();
        assertEq(spyVector, -1);
    }

    function test_CannotBlacklistWhitelistedAddress() public {
        vm.prank(owner);
        oracle.setWhitelisted(aiAgent, true);
        assertTrue(oracle.isWhitelisted(aiAgent));

        vm.prank(owner);
        vm.expectRevert(IFlexibleEnergyOracle.AddressWhitelisted.selector);
        oracle.setBlacklisted(aiAgent, true);
    }
    function test_DynamicPricingAdaptsToRlcCourse() public {
        // Проверяем цену при дефолтном курсе RLC ($0.33)
        // Для Tier 1 ($50 USD), стоимость в nRLC: (50 * 10^6 * 10^9) / 333333 = 150.00015 * 10^9 nRLC (~150 RLC)
        uint256 expectedCostNormal = oracle.getSubscriptionCost(1);
        assertApproxEqAbs(expectedCostNormal, 150 * 10**9, 10**9);

        // Владелец меняет цену RLC (RLC подорожал до $1.00)
        vm.prank(owner);
        oracle.setManualRlcPrice(1000000); // $1.00 (1 000 000)

        // Новая цена Tier 1 ($50 USD) в nRLC: (50 * 10^6 * 10^9) / 1000000 = 50 * 10^9 nRLC (ровно 50 RLC)
        uint256 expectedCostHigher = oracle.getSubscriptionCost(1);
        assertEq(expectedCostHigher, 50 * 10**9);
    }

    function test_SufficientRefundProcess() public {
        // Агент покупает подписку Tier 1 ($50 USD / 3 дня) при курсе RLC = $0.33 (~150 RLC)
        uint256 cost = oracle.getSubscriptionCost(1);
        vm.startPrank(aiAgent);
        rlc.approve(address(oracle), cost);
        oracle.purchaseSubscription(1);
        vm.stopPrank();

        // Оракул уходит на тех. обслуживание
        vm.prank(owner);
        oracle.setOracleStatus(IFlexibleEnergyOracle.OracleStatus.MAINTENANCE);

        // Имитируем прохождение 1 дня (86400 секунд). Осталось 2 дня из 3.
        vm.warp(block.timestamp + 1 days);

        uint256 balanceBefore = rlc.balanceOf(aiAgent);

        // Агент запрашивает возврат за оставшиеся 2 дня
        vm.prank(aiAgent);
        oracle.claimRefund();

        uint256 balanceAfter = rlc.balanceOf(aiAgent);
        uint256 refundReceived = balanceAfter - balanceBefore;

        // Должен получить примерно 2/3 от исходных 150 RLC (~100 RLC)
        assertApproxEqAbs(refundReceived, 100 * 10**9, 10**9);
        assertEq(oracle.subscriptionExpiry(aiAgent), block.timestamp);
    }
}
