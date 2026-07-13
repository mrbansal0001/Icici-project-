import os
import json
import csv
import time
import requests
import logging
import re
from collections import defaultdict
from shapely.geometry import Point, shape
from shapely.strtree import STRtree
from geopy.geocoders import Nominatim

# Setup Directories & Files
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_FILE = "/Users/tanishbansal/Library/CloudStorage/OneDrive-IITKanpur/Downloads/Datagov_Pincode_Boundaries.geojson"
OUTPUT_RAW_FILE = os.path.join(_SCRIPT_DIR, "signal6_nabh_v2_raw.csv")
OUTPUT_DENSITY_FILE = os.path.join(_SCRIPT_DIR, "signal6_nabh_v2_density.csv")
CACHE_FILE = os.path.join(_SCRIPT_DIR, "nominatim_cache.json")
LOG_FILE = os.path.join(_SCRIPT_DIR, "signal6_nabh_v2.log")

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_URL = "https://nabh.co/wp-admin/admin-ajax.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://nabh.co",
    "Referer": "https://nabh.co/find-a-healthcare-organisation/"
}

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", 
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", 
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", 
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", 
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

# Initialize Geolocator and Cache
geolocator = Nominatim(user_agent="nabh_v2_scraper")
geocode_cache = {}

if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r") as f:
            geocode_cache = json.load(f)
        logger.info(f"Loaded {len(geocode_cache)} cities from nominatim_cache.json")
    except Exception as e:
        logger.warning(f"Could not load cache: {e}")

def save_cache():
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(geocode_cache, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save cache: {e}")

def get_lat_long(city, state):
    key = f"{city},{state}"
    if key in geocode_cache:
        return geocode_cache[key]
    
    retries = 3
    for attempt in range(retries):
        try:
            location = geolocator.geocode(f"{city}, {state}, India", timeout=10)
            time.sleep(1) # Strict Nominatim policy
            result = [location.latitude, location.longitude] if location else [None, None]
            geocode_cache[key] = result
            save_cache()
            return result
        except Exception as e:
            logger.warning(f"Geocode fail for {key} (Attempt {attempt+1}/{retries}): {e}")
            time.sleep(2)
            
    # Failed completely
    geocode_cache[key] = [None, None]
    save_cache()
    return [None, None]

def get_cities(state):
    retries = 3
    for attempt in range(retries):
        try:
            res = requests.post(API_URL, headers=HEADERS, params={"action": "get_cities_by_state", "state": state}, timeout=10)
            if res.status_code == 200:
                raw = res.json()
                if isinstance(raw, list):
                    return [c.strip() for c in raw if c and c.strip()]
                elif isinstance(raw, dict) and "data" in raw:
                    if isinstance(raw["data"], list):
                        return [c.strip() for c in raw["data"] if c and c.strip()]
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch cities for {state} (Attempt {attempt+1}/{retries}): {e}")
            time.sleep(2)
    return []

def get_hospitals_page(state, lat, lng, page):
    retries = 3
    for attempt in range(retries):
        try:
            payload = {
                "action": "get_hospitals",
                "selectState": state,
                "selectedSpecText": "",
                "page": page,
                "lat": lat,
                "long": lng
            }
            res = requests.post(API_URL, headers=HEADERS, data=payload, timeout=15)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            logger.warning(f"Hospital fetch failed {state} page {page} (Attempt {attempt+1}/{retries}): {e}")
            time.sleep(2)
    return None

def extract_regex_pincode(address):
    if not address: return None
    match = re.search(r'\b[1-9][0-9]{5}\b', address)
    return match.group() if match else None

def main():
    logger.info("--- Starting NABH V2 Scraper (Spatial Mapping + Full States) ---")
    
    # 1. Load GeoJSON and build Spatial Index
    logger.info("Loading Datagov GeoJSON for precision mapping...")
    pincode_polygons = []
    try:
        with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
            for feature in geojson_data.get("features", []):
                geom = shape(feature["geometry"])
                pc = str(feature["properties"].get("Pincode", ""))
                if pc:
                    pincode_polygons.append((geom, pc))
        logger.info(f"Loaded {len(pincode_polygons)} polygons. Building R-Tree...")
    except Exception as e:
        logger.error(f"Failed to load GeoJSON: {e}")
        return

    geometries = [p[0] for p in pincode_polygons]
    rtree = STRtree(geometries)

    all_hospitals = {} # Use dict for immediate deduplication by key: (name, lat, lng)
    
    # 2. Extract Data
    for state in STATES:
        logger.info(f"🚀 Processing State: {state}")
        cities = get_cities(state)
        logger.info(f"   Found {len(cities)} cities.")
        
        for city in cities:
            lat, lng = get_lat_long(city, state)
            if lat is None or lng is None:
                continue
                
            page_data = get_hospitals_page(state, lat, lng, page=1)
            if not page_data:
                continue
                
            total_pages = page_data.get("pagination", {}).get("total_pages", 1)
            
            for page in range(1, total_pages + 1):
                if page > 1:
                    time.sleep(0.5)
                    page_data = get_hospitals_page(state, lat, lng, page=page)
                    if not page_data: continue
                
                for h in page_data.get("mapData", []):
                    name = str(h.get("name", "")).strip()
                    address = str(h.get("address", "")).strip()
                    h_lat = h.get("lat")
                    h_lng = h.get("lng")
                    
                    if not name: continue
                    
                    # Deduplication key
                    key = f"{name}_{h_lat}_{h_lng}"
                    if key not in all_hospitals:
                        all_hospitals[key] = {
                            "state": state,
                            "city": city,
                            "name": name,
                            "address": address,
                            "lat": h_lat,
                            "lng": h_lng,
                            "pincode": None
                        }
            time.sleep(0.5)

    logger.info(f"✅ Finished extraction. Collected {len(all_hospitals)} unique hospitals.")
    
    # 3. Spatial Mapping Phase
    logger.info("Executing Spatial Mapping...")
    mapped_count = 0
    fallback_count = 0
    
    density_map = defaultdict(int)
    final_records = []
    
    for key, h in all_hospitals.items():
        h_lat = h["lat"]
        h_lng = h["lng"]
        assigned_pincode = None
        
        # Try Spatial Match
        if h_lat and h_lng:
            try:
                pt = Point(float(h_lng), float(h_lat))
                idx = rtree.query(pt)
                if isinstance(idx, (list, tuple)) and len(idx) > 0:
                    idx = idx[0]
                elif hasattr(idx, 'size') and idx.size > 0: # numpy array
                    idx = idx[0]
                else:
                    idx = None
                    
                if idx is not None:
                    geom, pc = pincode_polygons[idx]
                    if geom.contains(pt):
                        assigned_pincode = pc
            except Exception:
                pass
                
        if assigned_pincode:
            mapped_count += 1
        else:
            # Fallback to Regex
            assigned_pincode = extract_regex_pincode(h["address"])
            if assigned_pincode:
                fallback_count += 1
                
        if assigned_pincode:
            h["pincode"] = assigned_pincode
            density_map[assigned_pincode] += 1
            final_records.append(h)
            
    logger.info(f"Spatial Mapping: {mapped_count} matched mathematically. {fallback_count} matched via regex fallback.")
    
    # 4. Save Raw Output
    logger.info("Saving outputs...")
    with open(OUTPUT_RAW_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["state", "city", "name", "address", "lat", "lng", "pincode"])
        writer.writeheader()
        writer.writerows(final_records)
        
    # 5. Save Density Output
    sorted_density = sorted(density_map.items(), key=lambda x: x[1], reverse=True)
    with open(OUTPUT_DENSITY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pincode", "nabh_hospital_count"])
        for pc, count in sorted_density:
            writer.writerow([pc, count])
            
    logger.info("🎉 SUCCESS! Saved signal6_nabh_v2_raw.csv and signal6_nabh_v2_density.csv")

if __name__ == "__main__":
    main()
