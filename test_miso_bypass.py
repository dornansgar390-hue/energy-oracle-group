import sys
from curl_cffi import requests
from selectolax.parser import HTMLParser

def main():
    print("Testing MISO RTDataAPIs page bypass...")
    url = "https://www.misoenergy.org/markets-and-operations/rtdataapis/"
    
    try:
        response = requests.get(url, impersonate="chrome120", timeout=15)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        
        if response.status_code == 200:
            parser = HTMLParser(response.text)
            links = []
            for a in parser.css("a"):
                href = a.attributes.get("href", "")
                text = a.text().strip()
                if any(x in href.lower() or x in text.lower() for x in ["lmp", "api", "xml", "json"]):
                    links.append((text, href))
            
            print(f"Found {len(links)} candidate API links:")
            for text, href in set(links):
                full_url = href if href.startswith("http") else "https://www.misoenergy.org" + href
                print(f"- {text}: {full_url}")
        else:
            print("Failed with non-200 status.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
