// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../../src/FlexibleEnergyOracle.sol";

/**
 * @title DeployOracle
 * @notice Forge script to deploy the FlexibleEnergyOracle contract on Arbitrum One Mainnet.
 */
contract DeployOracle is Script {
    function run() external {
        // Retrieve deployer private key from environment (.env)
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        // Target network addresses (Arbitrum One Mainnet defaults)
        address rlcTokenAddress = 0xe649e6a1F2afc63ca268C2363691ceCAF75CF47C; 
        address trustedEnclaveAddress = vm.envAddress("TRUSTED_ENCLAVE_ADDRESS"); 
        
        // iExec Hub Core Address on Arbitrum One Mainnet
        address iexecHubAddress = 0x30751A4D01074C5d336A41400D55097b94B6862f; 

        // Start broadcasting on-chain transactions
        vm.startBroadcast(deployerPrivateKey);

        // Fetch initial owner (or fall back to deployer's address if not provided)
        address initialOwnerAddress = vm.envOr("INITIAL_OWNER", vm.addr(deployerPrivateKey));

        // Deploy contract
        FlexibleEnergyOracle oracle = new FlexibleEnergyOracle(
            rlcTokenAddress, 
            iexecHubAddress, 
            trustedEnclaveAddress,
            initialOwnerAddress
        );

        console.log("Oracle deployed successfully on Arbitrum One Mainnet at:", address(oracle));

        vm.stopBroadcast();
    }
}
