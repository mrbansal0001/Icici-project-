import os
import csv
import json
import re
import time
import logging
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

try:
    from shapely.geometry import shape, Point
    from shapely.strtree import STRtree
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

PINCODE_RE = re.compile(r'^\d{6}$')

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_FILE = "/Users/tanishbansal/Library/CloudStorage/OneDrive-IITKanpur/Downloads/Datagov_Pincode_Boundaries.geojson"

log_file = os.path.join(_SCRIPT_DIR, "signal8_mapper.log")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def load_school_data():
    all_schools = []
    
    files = [
        "ib_schools_india.csv",
        "cbse_schools_india.csv",
        "icse_schools_india.csv" 
    ]
    
    for filename in files:
        filepath = os.path.join(_SCRIPT_DIR, filename)
        if os.path.exists(filepath):
            logger.info(f"Loading {filename}...")
            df = pd.read_csv(filepath)
            
            for _, row in df.iterrows():
                # Extract relevant fields. Some scrapers might name columns slightly differently.
                name = row.get("School_Name") or row.get("Name_Address") or ""
                address = row.get("Address") or row.get("Name_Address") or ""
                # Some datasets like ICSE are already aggregated with `school_count`
                # Handle lowercase 'pincode' column
                pincode_val = row.get("Pincode") if "Pincode" in row else row.get("pincode", "")
                pincode = str(pincode_val).strip().replace(".0", "")
                
                school_count = int(row.get("school_count", 1)) if "school_count" in row else 1
                
                board = row.get("Board", "Unknown")
                lat = row.get("lat") if "lat" in row else None
                lon = row.get("lon") if "lon" in row else None
                
                # If they are strings or NaN, handle them
                if pd.isna(lat) or pd.isna(lon):
                    lat = None
                    lon = None
                
                all_schools.append({
                    "name": name,
                    "address": address,
                    "pincode": pincode,
                    "school_count": school_count,
                    "board": board,
                    "lat": lat,
                    "lon": lon
                })
        else:
            logger.warning(f"File {filename} not found. Skipping.")
            
    return all_schools

def load_pincode_polygons():
    if not HAS_SHAPELY:
        logger.error("shapely is not installed. Spatial join will be skipped.")
        return [], []
        
    polygons = []
    pincodes_list = []
    
    logger.info(f"Loading GeoJSON from {GEOJSON_FILE}")
    try:
        with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                raw_pincode = props.get("Pincode") or props.get("pincode") or props.get("PINCODE")
                geom = feature.get("geometry")
                pincode = str(raw_pincode).strip().replace(".0", "") if raw_pincode is not None else None
                if pincode and PINCODE_RE.match(pincode) and geom:
                    poly_shape = shape(geom)
                    polygons.append(poly_shape)
                    pincodes_list.append(pincode)
    except Exception as e:
        logger.error(f"GeoJSON error: {e}")
        return [], []
        
    logger.info(f"Loaded {len(polygons)} polygons.")
    return polygons, pincodes_list

def geocode_missing_pincodes(schools):
    logger.info("Forward geocoding schools missing pincodes...")
    
    geolocator = Nominatim(user_agent="icici_bank_school_mapper")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1.5)
    
    cache_file = os.path.join(_SCRIPT_DIR, "geocoding_cache.json")
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cache = json.load(f)
        except Exception: pass
        
    updated = False
    polygons, pincodes_list = load_pincode_polygons()
    
    tree = None
    if polygons:
        logger.info("Building R-Tree Spatial Index...")
        tree = STRtree(polygons)
        
    for st in schools:
        p = st.get("pincode")
        if p and PINCODE_RE.match(str(p)):
            continue # Valid pincode already exists
            
        coords = None
        if st.get("lat") is not None and st.get("lon") is not None:
            coords = (st["lat"], st["lon"])
        else:
            # Needs geocoding
            query = f"{st['name']} {st['address']}".replace('\n', ' ').strip()
            # Truncate query to avoid Nominatim errors for too long queries
            query = query[:100] 
            
            if len(query) < 5:
                continue
            
            if query in cache:
                coords = cache[query]
            else:
                try:
                    location = geocode(query + " India")
                    if location:
                        coords = (location.latitude, location.longitude)
                    else:
                        coords = None
                    cache[query] = coords
                    updated = True
                    logger.info(f"Geocoded: {query[:30]}... -> {coords}")
                except Exception as e:
                    logger.error(f"Geocoding failed for {query[:30]}: {e}")
                    coords = None
                
        if coords and tree:
            st["lat"], st["lon"] = coords
            pt = Point(st["lon"], st["lat"])
            indices = tree.query(pt)
            for idx in indices:
                if polygons[idx].contains(pt):
                    st["pincode"] = pincodes_list[idx]
                    logger.info(f"Mapped {query[:30]}... to Pincode {st['pincode']}")
                    break
                    
    if updated:
        with open(cache_file, "w") as f:
            json.dump(cache, f)
            
    return schools

def main():
    schools = load_school_data()
    logger.info(f"Loaded {len(schools)} total schools across boards.")
    
    schools = geocode_missing_pincodes(schools)
    
    # Aggregate to final signal format
    pincode_counts = {}
    junk_count = 0
    for st in schools:
        p = st.get("pincode")
        if p and str(p) != 'nan' and PINCODE_RE.match(str(p)):
            pincode_counts[p] = pincode_counts.get(p, 0) + st.get("school_count", 1)
        else:
            junk_count += 1
            
    logger.info(f"Dropped {junk_count} schools with invalid/missing pincodes after mapping.")
    
    out_file = os.path.join(_SCRIPT_DIR, "signal8_final_pincode.csv")
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pincode", "premium_school_count"])
        for p, count in sorted(pincode_counts.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([p, count])
            
    logger.info(f"Success! Saved {len(pincode_counts)} unique pincodes to {out_file}.")
    
if __name__ == "__main__":
    main()
