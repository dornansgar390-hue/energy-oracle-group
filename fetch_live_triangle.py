import os
import json
import time
import requests
from datetime import datetime, timedelta

# Подтягиваем ваш ключ из системы (или вставьте строку вручную для теста)
GRIDSTATUS_KEY = os.environ.get("GRIDSTATUS_API_KEY")

if not GRIDSTATUS_KEY:
    raise ValueError("GRIDSTATUS_API_KEY environment variable not set.")

HEADERS = {
    "User-Agent": "iExec-Dashboard-Fetcher/2.0"
}

def query_dataset_hub(market, pnode):
    dataset_name = ""
    if market == "pjm":
        dataset_name = "pjm_lmp_day_ahead_hourly"
    elif market == "miso":
        dataset_name = "miso_lmp_day_ahead_hourly"
    elif market == "spp":
        dataset_name = "spp_lmp_day_ahead_hourly" # Assuming similar pattern to PJM

    url = f"https://api.gridstatus.io/v1/datasets/{dataset_name}/query"
    params = {
        "api_key": GRIDSTATUS_KEY,
        "limit": 24, # Запрашиваем последние 24 часа для построения красивого графика
        "sort": "timestamp.desc",
        "location": pnode,
        "start_date": "now-24h"
    }
    
    retries = 3
    for i in range(retries):
        try:
            res = requests.get(url, params=params, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                rows = res.json().get("data", [])
                seen_times = set()
                unique_rows = []

                for r in rows:
                    t = r.get("interval_start_utc")
                    if r.get("price_type", "LMP") == "LMP": 
                        if t not in seen_times:
                            seen_times.add(t)
                            unique_rows.append({"time": t, "price": float(r.get("lmp") or r.get("total_lmp"))})

                return unique_rows[::-1]
            elif res.status_code == 429:
                print(f"[WARNING] {market.upper()} вернул код: 429 (Too Many Requests) для URL: {res.url}. Повторная попытка через {2**(i+1)} секунд...")
                time.sleep(2**(i+1)) # Exponential backoff
            else:
                print(f"[ERROR] {market.upper()} вернул код: {res.status_code} для URL: {res.url}")
                break # Exit loop for other errors
        except Exception as e:
            print(f"[ERROR] Ошибка соединения с {market.upper()}: {e}")
            if i < retries - 1:
                print(f"[WARNING] Повторная попытка через {2**(i+1)} секунд...")
                time.sleep(2**(i+1))
            else:
                print(f"[ERROR] Максимальное количество повторных попыток достигнуто для {market.upper()}.")
    return []

def main():
    print("🚀 Запуск высокоскоростного сбора данных через Datasets API...")
    
    # Синхронно запрашиваем 3 главных хаба Америки
    # Исправление для PJM (Западный хаб — самый ликвидный, пишется через пробел)
    pjm_data = query_dataset_hub("pjm", "PJM WEST HUB") 
    time.sleep(1) # Add a delay between calls
    # Рабочий MISO
    miso_data = query_dataset_hub("miso", "INDIANA.HUB")
    time.sleep(1) # Add a delay between calls
    # Исправление для SPP (Южный или Северный хаб, пишутся капсом со словом HUB)
    spp_data = query_dataset_hub("spp", "SPP SOUTH HUB")  # Или "SPP NORTH HUB"

    print(f"PJM Data: {pjm_data}")
    print(f"MISO Data: {miso_data}")
    print(f"SPP Data: {spp_data}")
    
    # Собираем всё в один файл для дашборда
    dashboard_feed = {
        "last_update": int(time.time()),
        "pjm": pjm_data,
        "miso": miso_data,
        "spp": spp_data
    }
    
    # Сохраняем рядом с dashboard.html
    with open("live_data.json", "w", encoding="utf-8") as f:
        json.dump(dashboard_feed, f, indent=2)
        
    print("✅ Реальные данные успешно сохранены в 'live_data.json'!")

if __name__ == "__main__":
    main()
