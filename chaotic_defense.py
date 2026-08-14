import time
import uuid
import re
import datetime
from random import SystemRandom
from curl_cffi import requests
from selectolax.parser import HTMLParser

class ChaoticDefense:
    def __init__(self):
        self.crypto = SystemRandom()
        # Expanded list of safe, natural US weather and energy decoy sites for deep human simulation
        self.decoys = [
            "https://www.wikipedia.org",
            "https://www.github.com",
            "https://www.bing.com",
            "https://www.yahoo.com",
            "https://www.weather.com",
            "https://www.reddit.com",
            "https://www.stackoverflow.com",
            "https://www.microsoft.com",
            "https://www.amazon.com",
            "https://www.noaa.gov",               # National Oceanic and Atmospheric Administration (Weather/Wind)
            "https://www.eia.gov",                # US Energy Information Administration
            "https://www.wunderground.com",       # Weather Underground (Local wind/solar forecasting)
            "https://www.utilitydive.com",        # Leading power grid and utility sector news portal
            "https://www.power-eng.com"           # Power engineering and grid infrastructure news
        ]

    def make_decoy_request(self):
        """Simulates a natural human browsing a weather/energy related site before calling APIs."""
        decoy_url = self.crypto.choice(self.decoys)
        try:
            print(f"[DEFENSE] Human simulation: Browsing {decoy_url}...")
            # Use curl_cffi to mimic realistic Chrome TLS and browser fingerprints
            requests.get(decoy_url, impersonate="chrome120", timeout=5)
        except Exception as e:
            # Silently ignore decoy failures to prevent enclave execution aborts
            print(f"[DEFENSE-WARN] Decoy browse to {decoy_url} failed (skipped): {e}")
            pass

    def sleep_chaotic(self, min_sec=5.0, max_sec=45.0):
        """Applies completely unpredictable delay with millisecond precision to disrupt bot detectors."""
        delay = self.crypto.uniform(min_sec, max_sec)
        print(f"[DEFENSE] Applying chaotic delay: {delay:.3f} seconds...")
        time.sleep(delay)

def get_pjm_subscription_key():
    """
    Automatically retrieves the latest active PJM API key from the Data Miner 2 config.
    Self-healing mechanism to ensure continuous data feed updates.
    """
    url = "https://dataminer2.pjm.com/config/settings.json"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url, headers=headers, impersonate="chrome120", timeout=10)
        if res.status_code == 200:
            config = res.json()
            key = config.get("subscriptionKey")
            if key:
                print(f"[AUTO-KEY] Successfully retrieved fresh PJM subscription key: {key}")
                return key
    except Exception as e:
        print(f"[AUTO-KEY-ERROR] Failed to fetch PJM subscription key: {e}")
    # Fallback default key
    return "6a75d9f6d933401dbb4f36f8e70b95b3"

def get_gridstatus_commit_hash():
    """
    Automatically extracts the current frontend web commit hash of GridStatus to bypass request header validations.
    """
    base_url = "https://www.gridstatus.io"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        # 1. Fetch live page
        r = requests.get(f"{base_url}/live", headers=headers, impersonate="chrome120", timeout=10)
        if r.status_code == 200:
            parser = HTMLParser(r.text)
            # Find the main assets script
            for s in parser.css("script"):
                src = s.attributes.get("src", "")
                if "assets/index-" in src or "assets/useLogEvent-" in src:
                    # 2. Download the assets script
                    js_url = src if src.startswith("http") else base_url + src
                    js_res = requests.get(js_url, headers=headers, impersonate="chrome120", timeout=10)
                    if js_res.status_code == 200:
                        # Scan js file for SENTRY_RELEASE commit ID
                        match = re.search(r'SENTRY_RELEASE\s*=\s*\{\s*id\s*:\s*[\x22\x27]([a-f0-9]{40})[\x22\x27]', js_res.text)
                        if match:
                            commit_hash = match.group(1)
                            print(f"[AUTO-HASH] Successfully retrieved current GridStatus commit hash: {commit_hash}")
                            return commit_hash
    except Exception as e:
        print(f"[AUTO-HASH-ERROR] Failed to extract GridStatus commit hash: {e}")
    # Fallback default commit hash
    return "e5dc0bc991efe42f6548e246ff98c5ec26d94b9c"
