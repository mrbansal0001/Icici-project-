import os
import json
import csv
import time
import requests
import logging
from collections import defaultdict
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

# Setup Directories
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGSHARE_FILE = os.path.join(_SCRIPT_DIR, "signal7_ev_raw_plugshare.csv")
GEOJSON_FILE = "/Users/tanishbansal/Library/CloudStorage/OneDrive-IITKanpur/Downloads/Datagov_Pincode_Boundaries.geojson"
OUTPUT_FILE = os.path.join(_SCRIPT_DIR, "signal7_ev_density_plugshare_only.csv")

# Setup Logging
log_file = os.path.join(_SCRIPT_DIR, "signal7_plugshare_only.log")
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file), 
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def reverse_geocode_nominatim(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        'lat': lat,
        'lon': lon,
        'format': 'json',
        'addressdetails': 1
    }
    headers = {
        'User-Agent': 'ICICIAffluenceProject/1.0 (tanishbansal@example.com)'
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if 'address' in data and 'postcode' in data['address']:
                return data['address']['postcode'][:6]
    except Exception as e:
        pass
    return None

def main():
    logger.info("--- Starting PlugShare-Only EV Scraper (No Spatial Deduplication) ---")
    
    # 1. Load PlugShare Data
    if not os.path.exists(PLUGSHARE_FILE):
        logger.error(f"Missing {PLUGSHARE_FILE}. Cannot proceed.")
        return
        
    stations = []
    # Use a set to remove absolute 100% exact duplicates (same lat/lon down to decimal), 
    # but NOT the 30-meter physical radius deduplicator.
    seen = set()
    
    with open(PLUGSHARE_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row["lat"])
                lon = float(row["lon"])
                key = (lat, lon)
                if key not in seen:
                    seen.add(key)
                    stations.append({'lat': lat, 'lon': lon})
            except Exception:
                pass
                
    logger.info(f"Loaded {len(stations)} unique lat/lon stations strictly from PlugShare.")

    # 2. Load Datagov GeoJSON & Build R-Tree
    logger.info("Loading Datagov GeoJSON for precision mapping...")
    polygons = []
    pincodes = []
    
    with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)
        for feature in geojson_data.get("features", []):
            try:
                geom = shape(feature["geometry"])
                props = feature.get("properties", {})
                
                # Check all possible pincode keys
                pin = props.get("Pincode") or props.get("pincode") or props.get("PINCODE") or props.get("pin_code")
                if pin and str(pin).isdigit():
                    polygons.append(geom)
                    pincodes.append(str(pin).strip())
            except Exception:
                pass

    logger.info(f"Loaded {len(polygons)} polygons. Building R-Tree Spatial Index...")
    tree = STRtree(polygons)
    
    # 3. Spatially Assign Stations
    unmapped_stations = []
    pincode_counts = defaultdict(int)
    mapped_count = 0
    
    for s in stations:
        pt = Point(s['lon'], s['lat'])
        idx = tree.query(pt)
        if hasattr(idx, '__iter__'):
            matches = list(idx)
            if len(matches) > 0:
                match_idx = matches[0]
                pin = pincodes[match_idx]
                pincode_counts[pin] += 1
                mapped_count += 1
                continue
        elif idx is not None: # Older shapely versions return single int if point
            pin = pincodes[idx]
            pincode_counts[pin] += 1
            mapped_count += 1
            continue
            
        unmapped_stations.append(s)

    logger.info(f"Spatially assigned {mapped_count} stations instantly to precise pincodes.")
    
    # 4. Reverse Geocode Unmapped Fallbacks
    if unmapped_stations:
        logger.info(f"Reverse geocoding {len(unmapped_stations)} unmapped stations via Nominatim API...")
        logger.info(f"This will take ~{len(unmapped_stations)} seconds due to rate limits.")
        
        for i, s in enumerate(unmapped_stations):
            if i > 0 and i % 50 == 0:
                logger.info(f"Geocoded {i}/{len(unmapped_stations)}...")
                
            pin = reverse_geocode_nominatim(s['lat'], s['lon'])
            if pin and str(pin).isdigit() and len(str(pin)) == 6:
                pincode_counts[pin] += 1
            
            time.sleep(1) # Strict Nominatim rate limit
            
    # 5. Clean up & Save Output
    final_pincodes = {}
    valid_stations = 0
    drops = 0
    for pin, count in pincode_counts.items():
        if str(pin).isdigit() and len(str(pin)) == 6:
            final_pincodes[pin] = count
            valid_stations += count
        else:
            drops += count
            
    logger.info(f"Dropped {drops} stations due to invalid/junk pincodes after all fallback methods.")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pincode", "ev_charging_station_count"])
        for pin, count in sorted(final_pincodes.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([pin, count])
            
    logger.info(f"Done! Saved {len(final_pincodes)} unique pincodes to {OUTPUT_FILE}.")
    logger.info(f"Total pure PlugShare stations cleanly mapped: {valid_stations}")

if __name__ == "__main__":
    main()
