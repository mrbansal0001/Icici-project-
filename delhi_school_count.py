import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_delhi_outernorth_schools(base_url, output_file):
    print(f"1. Initiating Paginated Scrape on: {base_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    all_schools = []
    extracted_names = set() 
    page = 1
    
    # The Infinite Loop (Controlled by the Kill Switch below)
    while True:
        
        # Build the dynamic URL for the current page
        if page == 1:
            current_url = base_url
        else:
            clean_base = base_url.rstrip('/')
            current_url = f"{clean_base}/page/{page}/"
            
        print(f"   -> Scanning Page {page}: {current_url}")
        
        try:
            response = requests.get(current_url, headers=headers, verify=False, timeout=15)
            if response.status_code == 404:
                print("      -> Hit a 404 Wall. Pagination complete.")
                break
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"      -> 🚨 Connection failed on page {page}. Stopping pagination. Error: {e}")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        potential_blocks = soup.find_all(['div', 'li', 'tr', 'td'])
        schools_found_on_page = 0
        
        for block in potential_blocks:
            full_text = block.text.strip()
            pin_match = re.search(r'\b(110\d{3})\b', full_text)
            
            if pin_match:
                name_tag = block.find(['h2', 'h3', 'h4', 'strong', 'a', 'span'])
                if name_tag:
                    school_name = name_tag.text.strip()
                    
                    if len(school_name) > 5 and school_name not in extracted_names and "Read More" not in school_name:
                        school_data = {
                            'school_name': school_name,
                            'pincode': pin_match.group(1),
                            'district': 'Outer North Delhi',
                            'state': 'Delhi'
                        }
                        all_schools.append(school_data)
                        extracted_names.add(school_name)
                        schools_found_on_page += 1
        
        # --- THE KILL SWITCH ---
        # If it reaches Page 21 and finds nothing, it breaks the loop!
        if schools_found_on_page == 0:
            print("      -> 0 schools found. Reached the absolute end of the directory.")
            break
            
        print(f"      -> Successfully extracted {schools_found_on_page} schools.")
        
        page += 1       # Mathematically advance to the next page
        time.sleep(1)   # Give the server a 1-second breather

    print(f"\n2. Processing and Exporting Dataset...")
    if all_schools:
        df = pd.DataFrame(all_schools)
        df.to_csv(output_file, index=False)
        print(f"✅ EXPORT SUCCESSFUL: {len(df)} unique schools saved to {output_file}")
    else:
        print("❌ Failed to extract data.")

# --- Run the Script ---
if __name__ == "__main__":
    scrape_delhi_outernorth_schools(
        base_url="https://dmouternorth.delhi.gov.in/public-utility-category/schools/",
        output_file="/kaggle/working/delhi_outer_north_schools_full.csv"
    )

# do the same for all other government portals