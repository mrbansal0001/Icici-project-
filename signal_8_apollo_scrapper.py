# ============================================================
# Apollo Pharmacy Scraper — Signal 8
# ============================================================
# Strategy: Grid of coordinates covering all zones of 25 cities
#           Each city has 4-9 points covering suburbs too
#           Deduplication by storeId ensures no double counting
# ============================================================

import requests
import re
import time
import pandas as pd

API_URL = "https://api.apollo247.com/"

AUTH_TOKEN = "Bearer 3d1833da7020e0602165529446587434"

HEADERS = {
    "Authorization": AUTH_TOKEN,
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Origin": "https://www.apollopharmacy.in",
    "Referer": "https://www.apollopharmacy.in/medical-stores",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
}

GRAPHQL_QUERY = """
query getStoreLocatorData($storeLocatorDataInput: StoreLocatorDataInput!) {
  getStoreLocatorData(storeLocatorDataInput: $storeLocatorDataInput) {
    stores {
      name
      address {
        location
        coordinates {
          latitude
          longitude
          __typename
        }
        __typename
      }
      storeId
      __typename
    }
    __typename
  }
}
"""

# ── City grids — multiple points per city ────────────────────
# Format: (label, lat, lng)
# Each city covered by 4-9 points across all zones/suburbs

CITY_GRID = {
    "Mumbai": [
        ("South Mumbai",        18.9322, 72.8264),
        ("Bandra-Kurla",        19.0596, 72.8656),
        ("Andheri",             19.1136, 72.8697),
        ("Borivali",            19.2307, 72.8567),
        ("Thane",               19.2183, 72.9781),
        ("Navi Mumbai",         19.0330, 73.0297),
        ("Mira Road",           19.2952, 72.8544),
        ("Powai",               19.1176, 72.9060),
        ("Chembur",             19.0522, 72.9005),
    ],
    "Delhi": [
        ("Connaught Place",     28.6315, 77.2167),
        ("South Delhi",         28.5355, 77.2090),
        ("West Delhi",          28.6692, 77.1022),
        ("East Delhi",          28.6600, 77.3010),
        ("North Delhi",         28.7041, 77.1025),
        ("Dwarka",              28.5921, 77.0460),
        ("Rohini",              28.7495, 77.0680),
        ("Lajpat Nagar",        28.5677, 77.2433),
        ("Janakpuri",           28.6219, 77.0878),
    ],
    "Bengaluru": [
        ("City Center",         12.9716, 77.5946),
        ("Whitefield",          12.9698, 77.7499),
        ("Electronic City",     12.8399, 77.6770),
        ("Jayanagar",           12.9250, 77.5938),
        ("Hebbal",              13.0358, 77.5970),
        ("Koramangala",         12.9352, 77.6245),
        ("Marathahalli",        12.9591, 77.7009),
        ("Rajajinagar",         12.9915, 77.5521),
        ("Yelahanka",           13.1007, 77.5963),
    ],
    "Chennai": [
        ("City Center",         13.0827, 80.2707),
        ("Anna Nagar",          13.0850, 80.2101),
        ("Velachery",           12.9815, 80.2180),
        ("Tambaram",            12.9249, 80.1000),
        ("Porur",               13.0359, 80.1567),
        ("Sholinganallur",      12.9010, 80.2279),
        ("Adyar",               13.0012, 80.2565),
        ("Perambur",            13.1188, 80.2478),
    ],
    "Hyderabad": [
        ("Hitech City",         17.4435, 78.3772),
        ("Banjara Hills",       17.4126, 78.4483),
        ("Secunderabad",        17.4399, 78.4983),
        ("Kukatpally",          17.4849, 78.3996),
        ("LB Nagar",            17.3478, 78.5529),
        ("Gachibowli",          17.4401, 78.3489),
        ("Dilsukhnagar",        17.3688, 78.5247),
        ("Uppal",               17.4057, 78.5592),
    ],
    "Kolkata": [
        ("City Center",         22.5726, 88.3639),
        ("Salt Lake",           22.5958, 88.4147),
        ("South Kolkata",       22.4964, 88.3527),
        ("Howrah",              22.5958, 88.2636),
        ("Dum Dum",             22.6546, 88.3944),
        ("New Town",            22.6214, 88.4617),
        ("Jadavpur",            22.4971, 88.3711),
    ],
    "Pune": [
        ("City Center",         18.5204, 73.8567),
        ("Kothrud",             18.5074, 73.8077),
        ("Wakad",               18.5985, 73.7612),
        ("Hadapsar",            18.5018, 73.9258),
        ("Pimpri",              18.6186, 73.8037),
        ("Baner",               18.5590, 73.7868),
        ("Viman Nagar",         18.5679, 73.9143),
    ],
    "Ahmedabad": [
        ("City Center",         23.0225, 72.5714),
        ("Bopal",               23.0356, 72.4710),
        ("Satellite",           23.0300, 72.5200),
        ("Naranpura",           23.0507, 72.5570),
        ("Maninagar",           22.9949, 72.6071),
        ("Chandkheda",          23.1008, 72.5974),
        ("Thaltej",             23.0503, 72.5048),
    ],
    "Jaipur": [
        ("City Center",         26.9124, 75.7873),
        ("Malviya Nagar",       26.8560, 75.8069),
        ("Vaishali Nagar",      26.9181, 75.7376),
        ("Mansarovar",          26.8574, 75.7620),
        ("Tonk Road",           26.8710, 75.8090),
    ],
    "Lucknow": [
        ("City Center",         26.8467, 80.9462),
        ("Gomti Nagar",         26.8500, 81.0100),
        ("Aliganj",             26.8860, 80.9490),
        ("Hazratganj",          26.8467, 80.9462),
        ("Indira Nagar",        26.8730, 81.0020),
    ],
    "Chandigarh": [
        ("City Center",         30.7333, 76.7794),
        ("Mohali",              30.7046, 76.7179),
        ("Panchkula",           30.6942, 76.8606),
        ("Manimajra",           30.7282, 76.8333),
    ],
    "Indore": [
        ("City Center",         22.7196, 75.8577),
        ("Vijay Nagar",         22.7538, 75.8939),
        ("Palasia",             22.7271, 75.8806),
        ("Scheme 54",           22.7336, 75.9007),
    ],
    "Coimbatore": [
        ("City Center",         11.0168, 76.9558),
        ("RS Puram",            11.0040, 76.9536),
        ("Peelamedu",           11.0267, 77.0283),
        ("Gandhipuram",         11.0168, 76.9558),
    ],
    "Surat": [
        ("City Center",         21.1702, 72.8311),
        ("Adajan",              21.2116, 72.7980),
        ("Vesu",                21.1471, 72.7760),
        ("Athwa",               21.1782, 72.8178),
    ],
    "Nagpur": [
        ("City Center",         21.1458, 79.0882),
        ("Dharampeth",          21.1458, 79.0500),
        ("Sitabuldi",           21.1504, 79.0876),
        ("Manish Nagar",        21.1127, 79.0574),
    ],
    "Kochi": [
        ("Ernakulam",            9.9816, 76.2999),
        ("Kakkanad",             10.0159, 76.3419),
        ("Edapally",             10.0269, 76.3087),
        ("Fort Kochi",            9.9658, 76.2421),
    ],
    "Bhubaneswar": [
        ("City Center",         20.2961, 85.8245),
        ("Patia",               20.3526, 85.8178),
        ("Nayapalli",           20.2837, 85.8082),
        ("Chandrasekharpur",    20.3181, 85.8194),
    ],
    "Vadodara": [
        ("City Center",         22.3072, 73.1812),
        ("Alkapuri",            22.3072, 73.1693),
        ("Gotri",               22.3306, 73.1673),
        ("Manjalpur",           22.2677, 73.1784),
    ],
    "Visakhapatnam": [
        ("City Center",         17.6868, 83.2185),
        ("Gajuwaka",            17.6868, 83.2700),
        ("MVP Colony",          17.7231, 83.3012),
        ("Rushikonda",          17.7630, 83.3788),
    ],
    "Noida": [
        ("Sector 18",           28.5677, 77.3230),
        ("Sector 62",           28.6270, 77.3650),
        ("Greater Noida",       28.4744, 77.5040),
        ("Sector 137",          28.5102, 77.4013),
    ],
    "Gurugram": [
        ("DLF Phase 1",         28.4769, 77.0955),
        ("Sohna Road",          28.4213, 77.0413),
        ("Golf Course Road",    28.4421, 77.1022),
        ("Palam Vihar",         28.5082, 76.9935),
    ],
    "Patna": [
        ("City Center",         25.5941, 85.1376),
        ("Boring Road",         25.6093, 85.1314),
        ("Kankarbagh",          25.5891, 85.1560),
    ],
    "Guwahati": [
        ("City Center",         26.1445, 91.7362),
        ("Dispur",              26.1394, 91.7898),
        ("Geetanagar",          26.1537, 91.7661),
    ],
    "Mysuru": [
        ("City Center",         12.2958, 76.6394),
        ("Vijayanagar",         12.3213, 76.6216),
        ("Kuvempunagar",        12.2918, 76.6102),
    ],
}

# ── Helper ────────────────────────────────────────────────────
def extract_pincode(address):
    if not address:
        return None
    match = re.search(r'\b[1-9][0-9]{5}\b', address)
    return match.group() if match else None

def get_stores(lat, lng):
    payload = {
        "operationName": "getStoreLocatorData",
        "query": GRAPHQL_QUERY,
        "variables": {
            "storeLocatorDataInput": {
                "lat": lat,
                "lng": lng,
                "filters": {"skus": []}
            }
        }
    }
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=15)
        data = response.json()
        return data.get("data", {}).get("getStoreLocatorData", {}).get("stores", [])
    except Exception as e:
        print(f"    ⚠️ API error: {e}")
        return []

# ── Main Scraper ──────────────────────────────────────────────
print("🚀 Starting Apollo Pharmacy scraper with city grids...\n")

all_records = []
seen_store_ids = set()
total_calls = sum(len(points) for points in CITY_GRID.values())
print(f"Total API calls planned: {total_calls}\n")

for city_name, points in CITY_GRID.items():
    city_new = 0
    print(f"📍 {city_name} ({len(points)} grid points)")

    for label, lat, lng in points:
        stores = get_stores(lat, lng)

        for store in stores:
            store_id = store.get("storeId")
            if store_id in seen_store_ids:
                continue
            seen_store_ids.add(store_id)

            address = store.get("address", {}).get("location", "")
            pincode = extract_pincode(address)

            if pincode:
                all_records.append({
                    "city": city_name,
                    "zone": label,
                    "store_name": store.get("name", ""),
                    "address": address,
                    "pincode": pincode,
                    "store_id": store_id,
                })
                city_new += 1

        time.sleep(0.3)

    print(f"   ✅ {city_new} new stores with pincode found\n")

# ── Save Results ──────────────────────────────────────────────
df = pd.DataFrame(all_records)

signal8_apollo = (
    df.groupby("pincode")
    .size()
    .reset_index(name="apollo_pharmacy_count")
    .sort_values("apollo_pharmacy_count", ascending=False)
    .reset_index(drop=True)
)

df.to_csv("apollo_stores_raw.csv", index=False)
signal8_apollo.to_csv("signal8_apollo_pincode.csv", index=False)

print(f"✅ Scrape complete!")
print(f"   Total unique Apollo stores with pincode : {len(df)}")
print(f"   Unique pincodes                         : {len(signal8_apollo)}")
print(f"\nTop 10 pincodes by Apollo store density:")
print(signal8_apollo.head(10))