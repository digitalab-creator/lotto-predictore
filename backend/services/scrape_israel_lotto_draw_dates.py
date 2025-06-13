import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import time
import os

url = 'https://www.lotteryextreme.com/israel/lotto-results'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

draw_dates = set()
date_pattern = re.compile(r'(\d{2}\.\d{2}\.\d{4})')

# Start with the current month (GET)
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

while True:
    table = soup.find('table', class_='results3')
    rows = table.find_all('tr')
    i = 0
    should_stop = False
    while i < len(rows):
        row = rows[i]
        if 'class' in row.attrs and 'cy' in row.attrs['class']:
            date_info = row.find('td', class_='cx').get_text(strip=True)
            match = date_pattern.search(date_info)
            if match:
                date_str = match.group(1)
                try:
                    parsed_date = datetime.strptime(date_str, '%d.%m.%Y').date()
                    # Stop if we reach January 2024
                    if parsed_date <= datetime(2024, 1, 1).date():
                        print(f"🏴‍☠️ Reached {parsed_date}, stoppin' the scrape as ordered!")
                        should_stop = True
                        break
                    draw_dates.add(parsed_date.isoformat())
                    print(f"🏴‍☠️ Added date: {parsed_date.isoformat()}")
                except Exception as e:
                    print(f"⚠️ Could not parse date: {date_str} ({e})")
            else:
                print(f"⚠️ No date found in: {date_info}")
            i += 2
        else:
            i += 1
    
    if should_stop:
        break

    # Find the Previous month button
    prev_btn = soup.find('button', {'name': 'year_month_button'})
    if prev_btn and prev_btn.get('value'):
        prev_month = prev_btn['value']
        print(f"🏴‍☠️ Sailing to previous month: {prev_month}")
        response = requests.post(url, headers=headers, data={'year_month_button': prev_month})
        soup = BeautifulSoup(response.text, 'html.parser')
        time.sleep(0.5)  # Be polite to the server
    else:
        print("🏴‍☠️ No more previous months to fetch!")
        break

# Save the bounty to a JSON file
all_dates = sorted(draw_dates)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(backend_dir, 'israel_lotto_draw_dates.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(all_dates, f, ensure_ascii=False, indent=2)

print(f"🏴‍☠️ Arrr! The bounty of {len(all_dates)} draw dates be written to '{json_path}'") 