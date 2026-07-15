import time
import pandas as pd
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

def scrape_cbse_schools():
    print("Starting CBSE schools scraper...")
    options = uc.ChromeOptions()
    # options.add_argument('--headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')
    
    driver = uc.Chrome(options=options, version_main=149)
    url = "https://saras.cbse.gov.in/saras/AffiliatedList/ListOfSchdirReport"
    print(f"Navigating to {url}")
    
    driver.get(url)
    time.sleep(5)
    
    schools_data = []
    
    try:
        # Search by keyword or select state. SARAS usually has radio buttons.
        # Let's assume we select "State-wise" radio button
        try:
            state_radio = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "optlist_1")) # state-wise radio
            )
            state_radio.click()
            time.sleep(2)
        except Exception as e:
            print("Could not find state radio button:", e)

        # Loop through states (approx 36 states/UTs in India)
        # Note: Since there are ~30,000 CBSE schools, this will take a long time to scrape completely.
        # We'll just outline the extraction logic for a single page search for demonstration.
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find('table', {'id': 'myTable'})
        if table:
            rows = table.find_all('tr')[1:] # Skip header
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    aff_no = cols[1].text.strip()
                    state = cols[2].text.strip()
                    district = cols[3].text.strip()
                    name_address = cols[4].text.strip()
                    
                    pincode_match = re.search(r'\b\d{6}\b', name_address)
                    pincode = pincode_match.group(0) if pincode_match else ""
                    
                    schools_data.append({
                        'Affiliation_No': aff_no,
                        'Name_Address': name_address.replace('\n', ' '),
                        'State': state,
                        'District': district,
                        'Pincode': pincode,
                        'Board': 'CBSE'
                    })
        
        print(f"Extracted {len(schools_data)} CBSE schools from the current view...")

    except Exception as e:
        print(f"Error during CBSE scraping: {e}")
    
    finally:
        driver.quit()
        
    if schools_data:
        df = pd.DataFrame(schools_data)
        df = df.drop_duplicates(subset=['Affiliation_No'])
        df.to_csv("cbse_schools_india.csv", index=False)
        print(f"Successfully saved {len(df)} CBSE schools to cbse_schools_india.csv")
    else:
        print("No CBSE data extracted. DOM selectors might need updating or page was blocked.")

if __name__ == "__main__":
    scrape_cbse_schools()
