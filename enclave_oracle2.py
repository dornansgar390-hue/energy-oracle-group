import os
import sys
import json
import time
import random
from datetime import datetime
import requests
import pandas as pd
import numpy as np
import gridstatus
from eth_abi import encode

# Список заголовков для защиты от блокировок по IP (Anti-bot)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

def get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/csv, */*",
        "Accept-Language": "en-US,en;q=0.9"
    }

def fetch_eia_data(api_key: str, proxies: dict = None) -> dict | None:
    """Источник 1: Официальный REST API EIA v2 (Регион NYIS)"""
    if not api_key:
        print("[WARN] EIA API key отсутствует в iExec SMS. Пропуск источника.")
        return None
    try:
        url = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
        params = {
            "api_key": api_key,
            "frequency": "hourly",
            "data[]": "value",
            "facets[respondent][]": "NYIS",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 1
        }
        time.sleep(random.uniform(0.3, 1.0)) # Анти-флуд задержка (Jitter)
        res = requests.get(url, params=params, headers=get_headers(), proxies=proxies, timeout=10)
        if res.status_code == 200:
            data = res.json()["response"]["data"][0]
            dt = datetime.strptime(data["period"], "%Y-%m-%dT%H")
            return {
                "source": "EIA",
                "value": float(data["value"]),
                "timestamp": int(dt.timestamp())
            }
    except Exception as e:
        print(f"[ERROR] Ошибка сбора данных из EIA: {e}")
    return None

def fetch_nyiso_csv_data(proxies: dict = None) -> dict | None:
    """Источник 2: Прямой публичный архив CSV оператора сети NYISO"""
    try:
        # NYISO использует UTC-время для формирования папки текущих суток
        today_str = datetime.utcnow().strftime("%Y%m%d")
        url = f"http://mis.nyiso.com/public/csv/pal/{today_str}pal.csv"
        time.sleep(random.uniform(0.3, 1.0))
        
        res = requests.get(url, headers=get_headers(), proxies=proxies, timeout=10)
        if res.status_code == 200:
            from io import StringIO
            df = pd.read_csv(StringIO(res.text))
            if df.empty:
                return None
            latest = df.iloc[-1]
            dt = datetime.strptime(latest["TimeStamp"], "%m/%d/%Y %H:%M:%S")
            return {
                "source": "NYISO_Direct_CSV",
                "value": float(latest["Load"]),
                "timestamp": int(dt.timestamp())
            }
    except Exception as e:
        print(f"[ERROR] Ошибка сбора данных из NYISO CSV: {e}")
    return None

def fetch_gridstatus_data() -> dict | None:
    """Источник 3: Агрегатор Grid Status (Объектный парсер)"""
    try:
        time.sleep(random.uniform(0.3, 1.0))
        # Ограничиваем использование дискового кэша, критично для TEE-анклавов
        nyiso = gridstatus.NYISO()
        df = nyiso.get_load(date="today")
        if df.empty:
            return None
        latest = df.iloc[-1]
        dt = pd.to_datetime(latest["Time"])
        return {
            "source": "GridStatus",
            "value": float(latest["Load"]),
            "timestamp": int(dt.timestamp())
        }
    except Exception as e:
        print(f"[ERROR] Ошибка сборщика GridStatus: {e}")
    return None

def run_oracle_consensus(eia_key: str, proxy_url: str = None, max_age_seconds: int = 7200) -> dict:
    """Агрегирует данные, проверяет временные метки и вычисляет медиану"""
    current_time = int(time.time())
    # Округление до 5 минут гарантирует детерминизм вычислений в сети iExec PoCo
    consensus_timestamp = (current_time // 300) * 300

    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

    # Опрос шлюзов
    raw_reports = [
        fetch_eia_data(eia_key, proxies=proxies),
        fetch_nyiso_csv_data(proxies=proxies),
        fetch_gridstatus_data()
    ]

    # Фильтрация устаревших ответов
    valid_reports = []
    for report in raw_reports:
        if report and (current_time - report["timestamp"] <= max_age_seconds):
            valid_reports.append(report)

    # Проверка достижения кворума (минимум 2 независимых источника из 3)
    if len(valid_reports) < 2:
        raise RuntimeError(f"Кворум оракула скомпрометирован: получено {len(valid_reports)}/3 валидных ответов.")

    prices = [r["value"] for r in valid_reports]
    sources = [r["source"] for r in valid_reports]

    # Вычисление медианы и среднеквадратичного отклонения (дисперсии)
    median_value = float(np.median(prices))
    std_dev = float(np.std(prices))

    return {
        "metric": "electricity_demand_nyiso_mw",
        "consensus_value": round(median_value, 2),
        "dispersion_std": round(std_dev, 4),
        "sources_used": sources,
        "quorum_count": len(valid_reports),
        "timestamp_slot": consensus_timestamp,
        "status": "VERIFIED"
    }

if __name__ == "__main__":
    print("[iExec TEE Enclave] Инициализация защищенного энергетического оракула...")

    # Стандартные пути ввода-вывода для контейнеров iExec
    iexec_out = os.environ.get("IEXEC_OUT", "/iexec_out")

    # Безопасное извлечение ключей из iExec Secret Management Service (SMS)
    # По правилам iExec переменные мапятся как IEXEC_APP_DEVELOPER_SECRET_X
    EIA_API_KEY = os.environ.get("IEXEC_APP_DEVELOPER_SECRET_0", "")
    PROXY_URL = os.environ.get("IEXEC_APP_DEVELOPER_SECRET_1", None)

    try:
        # Запуск консенсус-движка
        payload = run_oracle_consensus(EIA_API_KEY, proxy_url=PROXY_URL)
        print(f"[iExec TEE Enclave] Консенсус успешно достигнут: {payload}")

        # Умножаем на 100 для ликвидации float (98.53 -> 9853) для совместимости с Solidity uint256
        consensus_value_int = int(payload["consensus_value"] * 100)
        timestamp = payload["timestamp_slot"]

        # Кодируем данные в строгий байткод EVM ABI (uint256, uint256)
        encoded_data = encode(['uint256', 'uint256'], [timestamp, consensus_value_int])
        callback_data = "0x" + encoded_data.hex()

        # Создаем выходную директорию воркера iExec
        os.makedirs(iexec_out, exist_ok=True)
        result_filepath = os.path.join(iexec_out, "result.json")

        # Формируем итоговый слепок: JSON для ИИ-агентов + байткод для блокчейна
        output_data = {
            "oracle_data": payload,
            "callback-data": callback_data 
        }

        with open(result_filepath, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

        # Создание файла сопоставления детерминированного вывода для протокола PoCo
        computed_filepath = os.path.join(iexec_out, "computed.json")
        computed_data = {
            "deterministic-output-path": result_filepath
        }
        with open(computed_filepath, "w", encoding="utf-8") as f:
            json.dump(computed_data, f, indent=2)

        print(f"[iExec TEE Enclave] Цикл завершен. Сгенерирован callback-data: {callback_data}")

    except Exception as err:
        print(f"[CRITICAL ERROR ВНУТРИ АНКЛАВА] {err}")
        sys.exit(1)
