import requests
from bs4 import BeautifulSoup
import time
import subprocess

# Targeting Pune Houses (Owner Only)
URL = "https://www.olx.in/pune_g4058997/for-rent-houses-apartments_c1723?filter=user_type_eq_owner"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
LAST_ID_FILE = "last_id.txt"

def notify(content):
    # Sends an Android notification
    subprocess.run(['termux-notification', '--title', 'New Direct Lead!', '--content', content])

def get_latest_id():
    try:
        res = requests.get(URL, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # OLX items usually have a specific data-aut-id or class
        item = soup.find('li', {'data-aut-id': 'itemBox'})
        return item['id'] if item else None
    except Exception as e:
        print(f"Connection error: {e}")
        return None

def main():
    print("Lead Finder is running... (Press Ctrl+C to stop)")
    while True:
        current_id = get_latest_id()
        
        # Load the last seen ID
        try:
            with open(LAST_ID_FILE, "r") as f:
                last_id = f.read().strip()
        except FileNotFoundError:
            last_id = ""

        if current_id and current_id != last_id:
            with open(LAST_ID_FILE, "w") as f:
                f.write(current_id)
            notify("A new property was just posted by an owner in Pune!")
            print(f"New Lead Found: {current_id}")
        
        # Check every 10 minutes to avoid getting blocked
        time.sleep(600)

if __name__ == "__main__":
    main()
