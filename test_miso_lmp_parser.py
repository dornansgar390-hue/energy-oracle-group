from curl_cffi import requests
from selectolax.parser import HTMLParser
import re
import json

def parse_miso_lmp():
    print("Fetching MISO homepage...")
    session = requests.Session()
    # Get homepage to extract dynamic API URLs using selectolax
    r = session.get("https://www.misoenergy.org/", impersonate="chrome120")
    if r.status_code != 200:
        print(f"Failed to load homepage: {r.status_code}")
        return

    doc = HTMLParser(r.text)
    api_base = "https://public-api.misoenergy.org" # default backup
    
    # Use selectolax to inspect React hydration configurations for public-api URLs
    for script in doc.css("script"):
        script_text = script.text()
        if "service_url" in script_text and "public-api.misoenergy.org" in script_text:
            match = re.search(r'"service_url"\s*:\s*"(https://public-api[^"]+)"', script_text)
            if match:
                # Extract base domain from match
                api_base = "/".join(match.group(1).split("/")[:3])
                print(f"[Selectolax] Discovered active public API base: {api_base}")
                break

    # Build the 5-min Consolidated LMP URL
    lmp_url = f"{api_base}/api/MarketPricing/GetLmpConsolidatedTable"
    print(f"Fetching 5-minute LMP data from: {lmp_url}")
    
    res = session.get(lmp_url, impersonate="chrome120")
    if res.status_code != 200:
        print(f"Failed to fetch LMP data: {res.status_code}")
        return

    data = res.json()
    five_min_data = data.get("LMPData", {}).get("FiveMinLMP", {})
    interval = five_min_data.get("DataInterval", "Unknown")
    nodes = five_min_data.get("PricingNode", [])
    
    print(f"\nInterval: {interval}")
    print("-" * 50)
    
    # Filter and display a few major hubs (e.g. INDIANA.HUB)
    target_nodes = ["INDIANA.HUB", "MICHIGAN.HUB", "MINN.HUB", "ILLINOIS.HUB"]
    for node in nodes:
        name = node.get("name")
        if name in target_nodes:
            lmp = node.get("LMP", "N/A")
            mcc = node.get("MCC", "N/A")
            mlc = node.get("MLC", "N/A")
            print(f"Node: {name:<15} | LMP: {lmp:>7} $/MWh | MCC: {mcc:>7} | MLC: {mlc:>7}")

if __name__ == "__main__":
    parse_miso_lmp()
