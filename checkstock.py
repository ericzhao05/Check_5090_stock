import requests
from bs4 import BeautifulSoup
import json
import time
import os
import random
import sys
from datetime import datetime
from requests_cache import CachedSession

# Configuration
CHECK_INTERVAL = (20, 60)  # Random delay between 20-60 seconds
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
]

STATUS_INDICATORS = {
    "checking": "🟡 Checking stock...       ",
    "in_stock": "🟢 IN STOCK DETECTED!     ",
    "out_of_stock": "🔴 Out of stock          "
}

# Initialize cached session
session = CachedSession('bestbuy_cache', expire_after=300)


def alert_sound():
    """Play alert sound only for in-stock status"""
    try:
        os.system('afplay /System/Library/Sounds/Ping.aiff')
        time.sleep(0.2)
        os.system('afplay /System/Library/Sounds/Ping.aiff')
    except:
        print('\a' * 2)
        sys.stdout.flush()


def print_status(status, message=""):
    """Print status with dynamic line replacement"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"[{timestamp}] {STATUS_INDICATORS[status]}{message}"

    if status == "checking":
        print(text, end='\r', flush=True)
    else:
        print(f"\033[K{text}", flush=True)


def check_stock():
    """Check stock status with anti-ban measures"""
    url = 'https://www.bestbuy.com/site/nvidia-geforce-rtx-5090-32gb-gddr7-graphics-card-dark-gun-metal/6614151.p?skuId=6614151'

    try:
        response = session.get(url, headers={
            'User-Agent': random.choice(USER_AGENTS),
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        })

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 300))
            print_status("checking", f"Rate limited - Waiting {retry_after}s")
            time.sleep(retry_after + 10)
            return False
        if response.status_code == 403:
            print("\n⚠️ Access forbidden - IP may be blocked")
            sys.exit(1)

        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        in_stock = False

        json_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        for script in json_scripts:
            try:
                json_data = json.loads(script.string)
                schemas = json_data if isinstance(json_data, list) else [json_data]

                for data in schemas:
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        offers = data.get('offers', {})
                        if isinstance(offers, list) and offers:
                            offers = offers[0]
                        if isinstance(offers, dict) and any(
                                x in offers.get('availability', '') for x in ['InStock', 'InStoreOnly']):
                            return True
            except:
                continue

        add_button = soup.find('button', {'data-button-state': 'ADD_TO_CART'})
        if add_button and 'disabled' not in add_button.attrs:
            return True

        return False

    except requests.exceptions.RequestException as e:
        print_status("checking", f"Network error: {str(e)}")
        return False


def main():
    print("\n🟢 Starting stock monitor (Press CTRL+C to stop)")
    try:
        while True:
            print_status("checking")

            try:
                stock_status = check_stock()
                if stock_status:
                    print_status("in_stock")
                    alert_sound()

                    # Continuous alert
                    while True:
                        alert_sound()
                        print_status("in_stock", "STILL IN STOCK - PRESS CTRL+C TO STOP")
                        time.sleep(1)
                else:
                    print_status("out_of_stock")

                # Random delay between checks
                delay = random.randint(*CHECK_INTERVAL)
                time.sleep(delay)

            except Exception as e:
                print_status("checking", f"Error: {str(e)}")
                time.sleep(60)

    except KeyboardInterrupt:
        print("\n🔴 Monitoring stopped")


if __name__ == "__main__":
    main()