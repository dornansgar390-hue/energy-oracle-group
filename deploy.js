const hre = require("hardhat");

async function main() {
  const rlcTokenAddress = "0x...RLC_TOKEN_ADDRESS_ON_ARBITRUM_SEPOLIA..."; // Replace with actual RLC token address on Arbitrum Sepolia
  const initialEnclaveAddress = "0x...INITIAL_ENCLAVE_ADDRESS..."; // Replace with the enclave's initial wallet address

  const SimpleEnergyOracle = await hre.ethers.getContractFactory("SimpleEnergyOracle");
  const oracle = await SimpleEnergyOracle.deploy(rlcTokenAddress, initialEnclaveAddress);

  await oracle.deployed();

  console.log(
    `SimpleEnergyOracle deployed to: ${oracle.address}`
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});