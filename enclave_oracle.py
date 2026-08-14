import os
import re
from selectolax.parser import HTMLParser
import sys
import uuid
import json
import time
import math
import datetime
from eth_abi import encode
from curl_cffi import requests

# Импортируем нашу систему защиты и авто-ключей
from chaotic_defense import ChaoticDefense, get_pjm_subscription_key, get_gridstatus_commit_hash

IEXEC_OUT = "/iexec_out"
RESULT_FILE = "/iexec_out/result.json"
COMPUTED_FILE = "/iexec_out/computed.json"
APP_ADDRESS = os.getenv("IEXEC_APP_ADDRESS", "0x0000000000000000000000000000000000000000")

# Порог спреда в $/МВт·ч для активации вектора арбитража
ARBITRAGE_THRESHOLD = 2.0

def scale_price(value):
    """Масштабирует float в int256 для Solidity (сохраняя 6 знаков после запятой)."""
    return int(round(float(value) * 1_000_000))

def get_pjm_lmp(defense_system):
    """Получает LMP для PJM West Hub (через макро-цену PJM-RTO с использованием обхода GridStatus API без ключей)."""
    defense_system.make_decoy_request()
    defense_system.sleep_chaotic(1.0, 5.0)

    print("[DEBUG] Fetching PJM LMP from GridStatus App-API (Bypass mode)...")
    url = "https://app-api.gridstatus.io/front-end/v1/datasets/isos_latest/query?return_format=json&json_schema=array-of-arrays"
    
    session_id = str(uuid.uuid4())
    commit_hash = get_gridstatus_commit_hash()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.gridstatus.io",
        "Referer": "https://www.gridstatus.io/",
        "x-gs-session-id": session_id,
        "x-source-url": "https://www.gridstatus.io/live",
        "x-gs-web-commit-hash": commit_hash,
        "X-Cache-Eligible": "true"
    }

    try:
        response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            data = response.json()
            rows = data.get("data", [])
            if rows:
                headers_row = rows[0]
                iso_idx = headers_row.index("iso")
                loc_idx = headers_row.index("latest_lmp_location")
                lmp_idx = headers_row.index("latest_lmp")
                
                for row in rows[1:]:
                    if row[iso_idx] == "pjm":
                        price = float(row[lmp_idx])
                        print(f"[DEBUG] PJM LMP ({row[loc_idx]}): {price} $/MWh")
                        return price
            print("[DEBUG] PJM row not found in isos_latest")
        else:
            print(f"[DEBUG] GridStatus API returned code {response.status_code}")
    except Exception as e:
        print(f"[DEBUG] Error fetching PJM LMP: {e}")
    return None

def get_miso_lmp(defense_system, hub_node="INDIANA.HUB"):
    """Получает точную LMP цену для MISO Indiana Hub напрямую с публичного API MISO (с динамическим поиском и хардкодом в качестве резерва)."""
    defense_system.make_decoy_request()
    defense_system.sleep_chaotic(1.0, 5.0)

    print(f"[DEBUG] Fetching MISO LMP for {hub_node}...")
    
    discovered_base = None
    miso_dynamic_success = False
    try:
        print("[DEBUG] Attempting dynamic MISO API discovery via selectolax...")
        homepage_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        }
        r = requests.get("https://www.misoenergy.org/", headers=homepage_headers, impersonate="chrome120", timeout=10)
        if r.status_code == 200:
            doc = HTMLParser(r.text)
            for script in doc.css("script"):
                script_text = script.text()
                if "service_url" in script_text and "public-api.misoenergy.org" in script_text:
                    match = re.search(r'"service_url"\s*:\s*"(https://public-api[^"]+)"', script_text)
                    if match:
                        discovered_base = "/".join(match.group(1).split("/")[:3])
                        print(f"[DEBUG] Dynamic Discovery SUCCESS! Active base URL: {discovered_base}")
                        miso_dynamic_success = True
                        break
        if not miso_dynamic_success:
            print("[DEBUG] MISO Homepage parsed, but dynamic URL not found.")
    except Exception as e:
        print(f"[DEBUG] Error during dynamic MISO API discovery: {e}")

    price_dynamic = None
    if miso_dynamic_success and discovered_base:
        url_dyn = f"{discovered_base}/api/MarketPricing/GetLmpConsolidatedTable"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Referer": "https://www.misoenergy.org/",
                "Origin": "https://www.misoenergy.org"
            }
            response = requests.get(url_dyn, headers=headers, impersonate="chrome120", timeout=15)
            if response.status_code == 200:
                data = response.json()
                if "LMPData" in data and "FiveMinLMP" in data["LMPData"]:
                    five_min = data["LMPData"]["FiveMinLMP"]
                    nodes = five_min.get("PricingNode", [])
                    for item in nodes:
                        if item.get("name") == hub_node:
                            lmp_value = item.get("LMP")
                            if lmp_value is not None:
                                price_dynamic = float(lmp_value)
                                print(f"[DEBUG] MISO LMP Dynamic ({hub_node}): {price_dynamic} $/MWh")
                                break
        except Exception as e:
            print(f"[DEBUG] Error fetching dynamic MISO LMP: {e}")
            miso_dynamic_success = False

    fallback_base = "https://public-api.misoenergy.org"
    url_fallback = f"{fallback_base}/api/MarketPricing/GetLmpConsolidatedTable"
    price_fallback = None
    miso_hardcoded_success = False
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.misoenergy.org/",
            "Origin": "https://www.misoenergy.org"
        }
        response = requests.get(url_fallback, headers=headers, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            data = response.json()
            if "LMPData" in data and "FiveMinLMP" in data["LMPData"]:
                five_min = data["LMPData"]["FiveMinLMP"]
                nodes = five_min.get("PricingNode", [])
                for item in nodes:
                    if item.get("name") == hub_node:
                        lmp_value = item.get("LMP")
                        if lmp_value is not None:
                            price_fallback = float(lmp_value)
                            print(f"[DEBUG] MISO LMP Fallback ({hub_node}): {price_fallback} $/MWh")
                            miso_hardcoded_success = True
                            break
    except Exception as e:
        print(f"[DEBUG] Error fetching fallback MISO LMP: {e}")

    if price_dynamic is not None:
        final_price = price_dynamic
        final_base = discovered_base
    else:
        final_price = price_fallback
        final_base = fallback_base

    return final_price, final_base, miso_dynamic_success, miso_hardcoded_success

def get_pjm_rto_load(defense_system):
    """Получает актуальную мгновенную нагрузку (Demand) всей системы PJM RTO с официального API PJM."""
    defense_system.make_decoy_request()
    defense_system.sleep_chaotic(1.0, 5.0)

    print("[DEBUG] Fetching PJM RTO load from official PJM API...")
    url = "https://api.pjm.com/api/v1/inst_load"
    
    key = get_pjm_subscription_key()
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            for item in items:
                if item.get("area") == "PJM RTO":
                    load_val = float(item.get("instantaneous_load"))
                    print(f"[DEBUG] PJM RTO Load: {load_val} MW")
                    return load_val
            print("[DEBUG] PJM RTO area load not found in inst_load items")
        else:
            print(f"[DEBUG] PJM inst_load API returned code {response.status_code}")
    except Exception as e:
        print(f"[DEBUG] Error fetching PJM load: {e}")
    return None

def get_miso_nsi_data(defense_system):
    """Получает чистый запланированный переток MISO."""
    defense_system.make_decoy_request()
    defense_system.sleep_chaotic(1.0, 5.0)

    url = "https://public-api.misoenergy.org/api/Interchange/GetNsi/FiveMinute"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
        if response.status_code == 200:
            data = response.json()
            instance = data.get("instance")
            if isinstance(instance, list) and len(instance) > 0:
                miso_val = instance[0].get("MISO")
                if miso_val is not None:
                    val = float(miso_val)
                    print(f"[DEBUG] MISO NSI: {val} MW")
                    return val
        print("[DEBUG] Failed to find MISO NSI.")
    except Exception as e:
        print(f"[DEBUG] Error fetching MISO NSI: {e}")
    return None
def get_rlc_price_usd(defense_system):
    """Получает текущую рыночную цену RLC/USD с помощью каскадного поиска (Binance -> Gate.io -> CoinGecko)"""
    defense_system.make_decoy_request()
    defense_system.sleep_chaotic(1.0, 3.0)
    
    # 1. Binance (без защиты, публичный тикер)
    try:
        print("[DEBUG] Fetching RLC price from Binance API...")
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=RLCUSDT", timeout=5)
        if r.status_code == 200:
            price = float(r.json()["price"])
            print(f"[DEBUG] Binance RLC price: ${price:.4f}")
            return price
    except Exception as e:
        print(f"[DEBUG] Binance RLC price failed: {e}")

    # 2. Gate.io
    try:
        print("[DEBUG] Fetching RLC price from Gate.io API...")
        r = requests.get("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=RLC_USDT", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                price = float(data[0]["last"])
                print(f"[DEBUG] Gate.io RLC price: ${price:.4f}")
                return price
    except Exception as e:
        print(f"[DEBUG] Gate.io RLC price failed: {e}")

    # 3. CoinGecko
    try:
        print("[DEBUG] Fetching RLC price from CoinGecko API...")
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=rlc&vs_currencies=usd", timeout=5)
        if r.status_code == 200:
            price = float(r.json()["rlc"]["usd"])
            print(f"[DEBUG] CoinGecko RLC price: ${price:.4f}")
            return price
    except Exception as e:
        print(f"[DEBUG] CoinGecko RLC price failed: {e}")

    print("[WARNING] All RLC price APIs failed. Returning None.")
    return None

def main():
    print("\n[iExec Enclave] Launching decentralized energy oracle...\n")

    defense = ChaoticDefense()
    defense.sleep_chaotic(5.0, 30.0)

    pjm_price = get_pjm_lmp(defense)
    miso_price, miso_base, miso_dyn_ok, miso_hc_ok = get_miso_lmp(defense)

    pjm_load = get_pjm_rto_load(defense)
    miso_nsi = get_miso_nsi_data(defense)
    
    # Get current RLC/USD market price
    rlc_price_float = get_rlc_price_usd(defense)
    rlc_price_scaled = scale_price(rlc_price_float) if rlc_price_float is not None else 0

    confidence = 100
    if pjm_load is None:
        confidence -= 15
    if miso_nsi is None:
        confidence -= 15

    # Write diagnostic report for the Web3 dashboard
    live_report = {
        "last_update": int(time.time()),
        "pjm_price": pjm_price,
        "miso_price": miso_price,
        "pjm_load": pjm_load,
        "miso_nsi": miso_nsi,
        "miso_dynamic_success": miso_dyn_ok,
        "miso_hardcoded_success": miso_hc_ok,
        "miso_api_base": miso_base,
        "rlc_price_usd": rlc_price_float,
        "confidence_score": confidence,
        "auto_key_updates": {
            "pjm_miner_key": get_pjm_subscription_key(),
            "gridstatus_commit_hash": get_gridstatus_commit_hash()
        }
    }
    with open("live_data.json", "w", encoding="utf-8") as f_live:
        json.dump(live_report, f_live, indent=2, ensure_ascii=False)

    if pjm_price is None or miso_price is None:
        print("\n[CRITICAL] Failed to fetch prices from one or both ISOs. Exiting.")
        sys.exit(1)

    price_spread = pjm_price - miso_price
    
    if price_spread > ARBITRAGE_THRESHOLD:
        arb_vector = 1
    elif price_spread < -ARBITRAGE_THRESHOLD:
        arb_vector = -1
    else:
        arb_vector = 0

    print(f"\n[RESULT] PJM Price: {pjm_price:.2f} | MISO Price: {miso_price:.2f}")
    print(f"[RESULT] Spread: {price_spread:.2f} | Vector: {arb_vector} | Confidence: {confidence}%")

    payload = encode(
        ['address', 'uint256', 'int256', 'int256', 'int256', 'int8', 'uint256', 'uint256'],
        [
            APP_ADDRESS,
            int(time.time()),
            scale_price(pjm_price),
            scale_price(miso_price),
            scale_price(price_spread),
            arb_vector,
            confidence,
            rlc_price_scaled
        ]
    )

    os.makedirs(IEXEC_OUT, exist_ok=True)
    callback_data = "0x" + payload.hex()

    with open(COMPUTED_FILE, "w") as f:
        json.dump({"deterministic-output-path": RESULT_FILE, "callback-data": callback_data}, f)

    with open(RESULT_FILE, "wb") as f:
        f.write(payload)

    print(f"\n[iExec Enclave] Ready. Data to send to smart contract: {callback_data}")

if __name__ == '__main__':
    main()
