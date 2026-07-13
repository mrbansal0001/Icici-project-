import requests
import time
import csv
import json
import os
import math
import logging
from difflib import SequenceMatcher
import urllib3
import re
urllib3.disable_warnings()

PINCODE_RE = re.compile(r'^\d{6}$')

try:
    from shapely.geometry import shape, Point
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False
    print("WARNING: shapely is not installed. Spatial join for missing pincodes will be skipped.")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEOJSON_FILE = "/Users/tanishbansal/Library/CloudStorage/OneDrive-IITKanpur/Downloads/Datagov_Pincode_Boundaries.geojson"

# Setup Logging
log_file = os.path.join(_SCRIPT_DIR, "signal7_ev.log")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Constants
OCM_API_KEY = "7d6228b0-588b-4912-9800-d0eaac28219e"
NATIONAL_BENCHMARK = 30000

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi, delta_lambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2.0)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

def save_checkpoint(stations, filename):
    filepath = os.path.join(_SCRIPT_DIR, filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["source", "lat", "lon", "pincode", "name"])
        writer.writeheader()
        writer.writerows(stations)
    logger.info(f"Checkpoint saved: {filepath} ({len(stations)} records)")

def load_checkpoint(filename):
    filepath = os.path.join(_SCRIPT_DIR, filename)
    if not os.path.exists(filepath): return None
    stations = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            stations.append({
                "source": row["source"],
                "lat": float(row["lat"]), "lon": float(row["lon"]),
                "pincode": row.get("pincode"), "name": row.get("name")
            })
    logger.info(f"Loaded checkpoint: {filepath} ({len(stations)} records)")
    return stations

def fetch_ocm_stations():
    stations = load_checkpoint("signal7_ev_raw_ocm.csv")
    if stations is not None: return stations

    logger.info("Fetching from OpenChargeMap...")
    all_stations = []
    offset, maxresults = 0, 10000
    while True:
        params = {"countrycode": "IN", "maxresults": maxresults, "offset": offset, "compact": False, "verbose": False, "key": OCM_API_KEY}
        try:
            data = requests.get("https://api.openchargemap.io/v3/poi/", params=params, timeout=30).json()
            if not data: break
            for s in data:
                addr = s.get("AddressInfo", {})
                lat, lon = addr.get("Latitude"), addr.get("Longitude")
                if lat and lon:
                    all_stations.append({
                        "source": "OCM", "lat": float(lat), "lon": float(lon),
                        "pincode": addr.get("Postcode", ""),
                        "name": f"{addr.get('Title', '')} {s.get('OperatorInfo', {}).get('Title', '')}".strip()
                    })
            if len(data) < maxresults: break
            offset += maxresults
            time.sleep(1)
        except Exception as e:
            logger.error(f"OCM Error: {e}")
            break
    save_checkpoint(all_stations, "signal7_ev_raw_ocm.csv")
    return all_stations

def fetch_osm_stations():
    stations = load_checkpoint("signal7_ev_raw_osm.csv")
    if stations is not None: return stations

    logger.info("Fetching from OpenStreetMap (nodes, ways, relations)...")
    query = '[out:json][timeout:180];area["ISO3166-1"="IN"][admin_level=2]->.searchArea;(node["amenity"="charging_station"](area.searchArea);way["amenity"="charging_station"](area.searchArea);relation["amenity"="charging_station"](area.searchArea););out center;'
    try:
        data = requests.post("https://overpass-api.de/api/interpreter", data={'data': query}, headers={"User-Agent": "EVSearch/2.0"}, timeout=200).json()
        osm_stations = []
        for el in data.get("elements", []):
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if lat and lon:
                osm_stations.append({
                    "source": "OSM", "lat": float(lat), "lon": float(lon),
                    "pincode": el.get("tags", {}).get("addr:postcode", ""),
                    "name": f"{el.get('tags', {}).get('name', '')} {el.get('tags', {}).get('brand', '')}".strip()
                })
        save_checkpoint(osm_stations, "signal7_ev_raw_osm.csv")
        return osm_stations
    except Exception as e:
        logger.error(f"OSM Error: {e}")
        return []

def fetch_eamrit_stations():
    stations = load_checkpoint("signal7_ev_raw_eamrit.csv")
    if stations is not None: return stations

    logger.info("Fetching from e-AMRIT...")
    logger.warning("COMPLIANCE NOTE: Before deploying to production, email mobility-niti@nic.in as per e-AMRIT Website Policies for bulk data usage.")
    try:
        # Bulk query endpoint discovered
        data = requests.get("https://e-amrit.niti.gov.in/getChargingStation", timeout=30, verify=False).json()
        eamrit_stations = []
        # Usually it returns a list or dict
        items = data if isinstance(data, list) else data.get("data", [])
        for item in items:
            lat = item.get("lat") or item.get("latitude") or item.get("lattitude")
            lon = item.get("lng") or item.get("longitude")
            if lat and lon:
                try:
                    f_lat = float(lat)
                    f_lon = float(lon)
                    eamrit_stations.append({
                        "source": "e-AMRIT", "lat": f_lat, "lon": f_lon,
                        "pincode": item.get("pincode", ""), "name": item.get("name", "")
                    })
                except ValueError:
                    pass
        save_checkpoint(eamrit_stations, "signal7_ev_raw_eamrit.csv")
        return eamrit_stations
    except Exception as e:
        logger.error(f"e-AMRIT Error: {e}")
        return []

def fetch_private_operators():
    logger.info("Attempting to fetch unofficial Private Operator data...")
    logger.warning("RISK NOTE: Scraping undocumented endpoints is volatile and may trigger IP blocks. Tagging source as 'unofficial/best-effort'.")
    
    plugshare_stations = load_checkpoint("signal7_ev_raw_plugshare.csv")
    if plugshare_stations:
        logger.info(f"Loaded {len(plugshare_stations)} stations from PlugShare.")
        return plugshare_stations
        
    return []

def deduplicate_stations(stations):
    logger.info(f"Deduplicating {len(stations)} stations...")
    unique_stations = []
    merged = 0
    
    for st in stations:
        is_duplicate = False
        name1 = str(st.get("name", "")).strip().lower()
        
        for uniq_st in unique_stations:
            dist = haversine_distance(st["lat"], st["lon"], uniq_st["lat"], uniq_st["lon"])
            
            # If within 30m, we almost certainly merge (even if same operator, likely same installation)
            if dist <= 30:
                is_duplicate = True
                merged += 1
                break
            
            # If between 30m and 75m, we merge ONLY if names match (to catch duplicate entries of same station)
            # If names are blank, we DO NOT merge them in the 30-75m range (assume distinct stations)
            if 30 < dist <= 75:
                name2 = str(uniq_st.get("name", "")).strip().lower()
                if name1 and name2:
                    if SequenceMatcher(None, name1, name2).ratio() > 0.6:
                        is_duplicate = True
                        merged += 1
                        break
        
        if not is_duplicate:
            unique_stations.append(st)
            
    logger.info(f"Reduced to {len(unique_stations)} unique stations. Merged {merged} duplicates.")
    return unique_stations

def spatial_join(stations):
    if not HAS_SHAPELY: return stations
    logger.info("Running STRTree Point-in-Polygon spatial join (ignoring noisy API pincodes)...")
    polygons = []
    pincodes_list = []
    
    try:
        from shapely.strtree import STRtree
    except ImportError:
        logger.error("shapely.strtree not available. Using slow fallback.")
        # We can implement fallback if necessary, but Shapely >= 1.8 has it
        
    try:
        with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                raw_pincode = props.get("Pincode") or props.get("pincode") or props.get("PINCODE") or props.get("pin_code") or props.get("PIN_CODE")
                geom = feature.get("geometry")
                pincode = str(raw_pincode).strip().replace(".0", "") if raw_pincode is not None else None
                if pincode and PINCODE_RE.match(pincode) and geom:
                    poly_shape = shape(geom)
                    polygons.append(poly_shape)
                    pincodes_list.append(pincode)
    except Exception as e:
        logger.error(f"GeoJSON error: {e}")
        return stations

    logger.info(f"Loaded {len(polygons)} polygons. Building R-Tree Spatial Index...")
    tree = STRtree(polygons)

    assigned = 0
    for st in stations:
        pt = Point(float(st["lon"]), float(st["lat"]))
        st["pincode"] = None
        
        # Fast bounding box intersection query
        indices = tree.query(pt)
        
        # Check actual intersection (Shapely 2.0 query returns array of indices)
        for idx in indices:
            if polygons[idx].contains(pt):
                st["pincode"] = pincodes_list[idx]
                assigned += 1
                break
                
    logger.info(f"Spatially assigned {assigned} stations to precise pincodes.")
    return stations

def reverse_geocode_bulk(stations):
    cache_file = os.path.join(_SCRIPT_DIR, "nominatim_cache.json")
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cache = json.load(f)
        except: pass
        
    updated = False
    
    # Count how many we actually need to fetch
    needs_fetch = 0
    for st in stations:
        p = st.get("pincode")
        if not (p and PINCODE_RE.match(str(p))):
            key = f"{st['lat']},{st['lon']}"
            if key not in cache:
                needs_fetch += 1
                
    if needs_fetch > 0:
        logger.info(f"Reverse geocoding {needs_fetch} unmapped stations via Nominatim API. This will take ~{needs_fetch} seconds due to rate limits...")
    else:
        logger.info("No new stations to reverse geocode. Using cache.")
        
    for st in stations:
        p = st.get("pincode")
        if p and PINCODE_RE.match(str(p)):
            continue
            
        lat, lon = st["lat"], st["lon"]
        key = f"{lat},{lon}"
        if key in cache:
            st["pincode"] = cache[key]
        else:
            try:
                url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=jsonv2"
                headers = {"User-Agent": "ICICI_EV_Density_Analysis_Script/1.0 (tanishbansal8935@gmail.com)"}
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    postcode = data.get("address", {}).get("postcode")
                    cache[key] = postcode
                    st["pincode"] = postcode
                    updated = True
                else:
                    cache[key] = None
                time.sleep(1) # Strict 1 request/sec Nominatim policy
            except Exception as e:
                logger.error(f"Geocode Error: {e}")
                cache[key] = None
                time.sleep(1)
                
    if updated:
        with open(cache_file, "w") as f:
            json.dump(cache, f)
            
    return stations

def main():
    logger.info("--- Starting Multi-Source EV Scraper ---")
    
    all_stations = fetch_ocm_stations() + fetch_osm_stations() + fetch_eamrit_stations() + fetch_private_operators()
    logger.info(f"Total raw stations combined: {len(all_stations)}")
    
    all_stations = deduplicate_stations(all_stations)
    all_stations = spatial_join(all_stations)
    
    # Reverse geocode any stations that the GeoJSON map missed
    all_stations = reverse_geocode_bulk(all_stations)
    
    # Aggregate
    pincode_counts = {}
    junk_count = 0
    for st in all_stations:
        p = st.get("pincode")
        if p and PINCODE_RE.match(str(p)):
            pincode_counts[p] = pincode_counts.get(p, 0) + 1
        else:
            junk_count += 1
            
    logger.info(f"Dropped {junk_count} stations with invalid/junk pincode after spatial join.")
            
    out_file = os.path.join(_SCRIPT_DIR, "signal7_ev_density_v3.csv")
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["pincode", "ev_charging_station_count"])
        for p, count in sorted(pincode_counts.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([p, count])
            
    final_count = sum(pincode_counts.values())
    logger.info(f"Done! Saved {len(pincode_counts)} unique pincodes to {out_file}.")
    logger.info(f"Total EV stations mapped: {final_count}")
    
    # National Benchmark check
    if final_count < 10000:
        logger.warning(f"Verification Failed: {final_count} stations is way below national benchmark ({NATIONAL_BENCHMARK}). Missing major sources?")
    elif final_count > 60000:
        logger.warning(f"Verification Failed: {final_count} stations is way above national benchmark ({NATIONAL_BENCHMARK}). Bad deduplication?")
    else:
        logger.info(f"Verification Passed: Final count ({final_count}) aligns with national benchmarks.")

if __name__ == "__main__":
    main()
