// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @dev Минимальный интерфейс токена ERC-20 для работы с iExec RLC.
 * Напоминание для Cline: Токен RLC использует разрядность 9 decimals (nRLC).
 */
interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/**
 * @title SimpleEnergyOracle
 * @dev Децентрализованный B2B-шлюз подписки на телеметрию для ИИ-агентов.
 * Реализует простую и безопасную логику фиксированного доступа на 3 дня (72 часа).
 */
contract SimpleEnergyOracle {
    address public owner;
    address public trustedEnclave; // Публичный адрес кошелька, привязанного к вашему TEE-анклаву
    IERC20 public rlcToken;        // Смарт-контракт токена iExec RLC в целевой сети

    // 150 RLC с учетом разрядности 9 знаков после запятой (150 * 10^9 nRLC)
    uint256 public accessPrice = 150 * 10**9; 
    uint256 public constant DURATION = 3 days; // Шаг продления подписки

    string public currentData; // Хранилище последней валидной медианы цен телеметрии

    // Маппинг для отслеживания дедлайна подписки каждого ИИ-агента
    mapping(address => uint256) public accessExpiredAt;

    event TelemetryUpdated(uint256 indexed timestamp);
    event SubscriptionPurchased(address indexed buyer, uint256 newExpiry);
    event FundsWithdrawn(address indexed owner, uint256 amount);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not contract owner");
        _;
    }

    modifier onlyEnclave() {
        require(msg.sender == trustedEnclave, "Only TEE enclave allowed");
        _;
    }

    constructor(address _rlcTokenAddress, address _trustedEnclaveAddress) {
        owner = msg.sender;
        rlcToken = IERC20(_rlcTokenAddress);
        trustedEnclave = _trustedEnclaveAddress;
    }

    /**
     * @notice Функция для TEE-анклава. Обновляет телеметрию в памяти блокчейна.
     * @param _json Строка формата JSON, содержащая очищенную медиану данных.
     */
    function updateTelemetry(string memory _json) external onlyEnclave {
        currentData = _json;
        emit TelemetryUpdated(block.timestamp);
    }

    /**
     * @notice Функция для ИИ-агента. Покупка или продление доступа на 3 дня.
     * @dev Требует предварительного вызова функции approve() на контракте токена RLC.
     */
    function buyAccess() external {
        // Списываем 150 RLC с кошелька ИИ-агента на баланс этого смарт-контракта
        require(
            rlcToken.transferFrom(msg.sender, address(this), accessPrice), 
            "RLC payment failed"
        );
        
        // Корректно рассчитываем время: сдвигаем дедлайн вперед
        if (accessExpiredAt[msg.sender] < block.timestamp) {
            // Если подписка истекла или покупается впервые
            accessExpiredAt[msg.sender] = block.timestamp + DURATION;
        } else {
            // Если подписка еще активна — честно прибавляем 3 дня к остатку
            accessExpiredAt[msg.sender] += DURATION;
        }

        emit SubscriptionPurchased(msg.sender, accessExpiredAt[msg.sender]);
    }

    /**
     * @notice Бесплатное (view) чтение телеметрии для ИИ-агентов с активной подпиской.
     * @return Текстовая строка (JSON) с верифицированными данными оракула.
     */
    function getTelemetry() external view returns (string memory) {
        require(accessExpiredAt[msg.sender] >= block.timestamp, "Buy access first");
        return currentData;
    }

    /**
     * @notice Вывод всех накопленных токенов RLC на кошелек владельца.
     * @dev Защищено модификатором onlyOwner, исключает застревание средств.
     */
    function withdrawRLC() external onlyOwner {
        uint256 contractBalance = rlcToken.balanceOf(address(this));
        require(contractBalance > 0, "No RLC available to withdraw");
        
        require(
            rlcToken.transfer(owner, contractBalance), 
            "Withdrawal transfer failed"
        );
        
        emit FundsWithdrawn(owner, contractBalance);
    }

    /**
     * @notice Возможность изменить цену подписки при изменении рыночной конъюнктуры.
     */
    function setAccessPrice(uint256 _newPriceInNRLC) external onlyOwner {
        accessPrice = _newPriceInNRLC;
    }

    /**
     * @notice Перенос прав владения контрактом.
     */
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Invalid address");
        emit OwnershipTransferred(owner, _newOwner);
        owner = _newOwner;
    }
}
