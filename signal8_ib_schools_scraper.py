import time
import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

def scrape_ib_schools():
    print("Starting IB schools scraper...")
    # Setup undetected_chromedriver
    options = uc.ChromeOptions()
    # options.add_argument('--headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')
    
    driver = uc.Chrome(options=options, version_main=149)
    
    url = "https://www.ibo.org/programmes/find-an-ib-school/?SearchFields.Country=IN"
    print(f"Navigating to {url}")
    driver.get(url)
    
    time.sleep(10) # Wait out the Cloudflare challenge
    
    schools_data = []
    
    try:
        # Wait for map to appear
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "Map"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        map_div = soup.find('div', class_='Map')
        
        if map_div and 'data-map-2' in map_div.attrs:
            import json
            data = json.loads(map_div['data-map-2'])
            schools = data.get('data', [])
            print(f"Found {len(schools)} schools in JSON map data!")
            
            for st in schools:
                schools_data.append({
                    'School_Name': st.get('title', ''),
                    'Address': st.get('url', ''),
                    'Pincode': '', # We have lat/lon, pincode mapper will handle it
                    'lat': st.get('lat'),
                    'lon': st.get('lng'),
                    'Board': 'IB'
                })
        else:
            print("Could not find map data JSON on page.")
        
        print(f"Extracted {len(schools_data)} schools...")
                
    except Exception as e:
        print(f"An error occurred or we were blocked: {e}")
        print("Page Title:", driver.title)
        
    finally:
        driver.quit()
        
    # Save to CSV
    if schools_data:
        df = pd.DataFrame(schools_data)
        df = df.drop_duplicates(subset=['School_Name'])
        df.to_csv("ib_schools_india.csv", index=False)
        print(f"Successfully saved {len(df)} IB schools to ib_schools_india.csv")
    else:
        print("No data extracted. Cloudflare might have blocked the request.")

if __name__ == "__main__":
    scrape_ib_schools()
