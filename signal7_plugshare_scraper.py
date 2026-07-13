import requests
import json
import time
import os
import csv
import logging

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(_SCRIPT_DIR, "signal7_plugshare.log")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# The user's freshly captured token
PLUGSHARE_TOKEN = "Basic d2ViX3YyOkVOanNuUE54NHhXeHVkODU="

def scrape_plugshare():
    logger.info("Starting PlugShare India Grid Scrape...")
    
    # India bounding box roughly
    lat_min, lat_max = 8, 38
    lon_min, lon_max = 68, 98
    step = 1.0 # 1 degree grid
    
    all_stations = {}
    
    total_grids = int((lat_max - lat_min)/step) * int((lon_max - lon_min)/step)
    count = 0
    
    for lat_start in range(lat_min, lat_max, int(step)):
        for lon_start in range(lon_min, lon_max, int(step)):
            count += 1
            center_lat = lat_start + (step/2.0)
            center_lon = lon_start + (step/2.0)
            
            url = f"https://www.plugshare.com/api/v3/locations/region?spanLat={step}&spanLng={step}&latitude={center_lat}&longitude={center_lon}&count=1000"
            headers = {
                "Authorization": PLUGSHARE_TOKEN,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            }
            
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for st in data:
                        # Deduplicate by PlugShare ID
                        all_stations[st["id"]] = {
                            "source": f"PlugShare-{st.get('network_id', 'unknown')}",
                            "lat": st.get("latitude"),
                            "lon": st.get("longitude"),
                            "name": st.get("name")
                        }
                elif resp.status_code == 401:
                    logger.error("Token Expired or Invalid!")
                    return all_stations
            except Exception as e:
                logger.error(f"Error fetching grid {center_lat},{center_lon}: {e}")
                
            if count % 50 == 0:
                logger.info(f"Progress: {count}/{total_grids} grids checked. Stations found so far: {len(all_stations)}")
            time.sleep(0.1) # Be polite
            
    return list(all_stations.values())

def main():
    stations = scrape_plugshare()
    logger.info(f"Finished scraping! Total unique stations recovered: {len(stations)}")
    
    out_file = os.path.join(_SCRIPT_DIR, "signal7_ev_raw_plugshare.csv")
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "lat", "lon", "name"])
        writer.writeheader()
        for st in stations:
            writer.writerow(st)
    logger.info(f"Saved to {out_file}")

if __name__ == "__main__":
    main()
