## one time load - downloads required bhavcopies

import os
import time
import requests
import pandas as pd
from io import BytesIO
from zipfile import ZipFile


# directory to store data
output_dir = "data/raw_fo"
os.makedirs(output_dir, exist_ok=True)

# Generate all weekdays between Jan 2021 and Dec 2023
dates = pd.bdate_range(start="2021-01-01", end="2023-12-31")

# browser headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Connection': 'keep-alive'
}

for dt in dates:

    year = dt.strftime("%Y")
    month = dt.strftime("%b").upper()
    day_str = dt.strftime("%d%b%Y").upper()
    
    url = f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{year}/{month}/fo{day_str}bhav.csv.zip"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        # check status
        if response.status_code == 200:
            with ZipFile(BytesIO(response.content)) as z:
                z.extractall(output_dir)
            print(f"Successfully downloaded: {day_str}")
        else:
            print(f"Skipped {day_str} (Status: {response.status_code} - likely a holiday)")
            
    except Exception as e:
        print(f"Error fetching {day_str}: {e}")
        
    time.sleep(1) # delay to prevent request blocking