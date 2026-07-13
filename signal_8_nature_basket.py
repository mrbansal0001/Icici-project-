# ============================================================
# Nature's Basket — Signal 8
# ============================================================
# Only 31-35 stores across 4 cities — hardcoded directly
# Source: naturesbasket.co.in store locator
# ============================================================

import pandas as pd

# All known Nature's Basket stores with pincodes
# Source: naturesbasket.co.in/store-locator
STORES = [
    # Mumbai
    {"city": "Mumbai", "store_name": "Bandra",              "address": "Hill Road, Bandra West, Mumbai",               "pincode": "400050"},
    {"city": "Mumbai", "store_name": "Juhu",                "address": "Juhu Tara Road, Juhu, Mumbai",                 "pincode": "400049"},
    {"city": "Mumbai", "store_name": "Andheri",             "address": "Lokhandwala Complex, Andheri West, Mumbai",    "pincode": "400053"},
    {"city": "Mumbai", "store_name": "Powai",               "address": "Hiranandani Gardens, Powai, Mumbai",           "pincode": "400076"},
    {"city": "Mumbai", "store_name": "Malad",               "address": "Inorbit Mall, Malad West, Mumbai",             "pincode": "400064"},
    {"city": "Mumbai", "store_name": "Vashi",               "address": "Sector 17, Vashi, Navi Mumbai",                "pincode": "400703"},
    {"city": "Mumbai", "store_name": "Chembur",             "address": "Basant Park, Chembur, Mumbai",                 "pincode": "400071"},
    {"city": "Mumbai", "store_name": "Santacruz",           "address": "Santacruz West, Mumbai",                       "pincode": "400054"},
    {"city": "Mumbai", "store_name": "Breach Candy",        "address": "Breach Candy, Mumbai",                         "pincode": "400026"},
    {"city": "Mumbai", "store_name": "Kemps Corner",        "address": "Kemps Corner, Mumbai",                         "pincode": "400036"},
    {"city": "Mumbai", "store_name": "Versova",             "address": "Versova, Andheri West, Mumbai",                "pincode": "400061"},
    {"city": "Mumbai", "store_name": "Goregaon",            "address": "Goregaon West, Mumbai",                        "pincode": "400104"},
    {"city": "Mumbai", "store_name": "Thane",               "address": "Viviana Mall, Thane West",                     "pincode": "400601"},
    {"city": "Mumbai", "store_name": "Mulund",              "address": "Mulund West, Mumbai",                          "pincode": "400080"},
    # Bengaluru
    {"city": "Bengaluru", "store_name": "Koramangala",      "address": "Koramangala 5th Block, Bengaluru",             "pincode": "560095"},
    {"city": "Bengaluru", "store_name": "Indiranagar",      "address": "100 Feet Road, Indiranagar, Bengaluru",        "pincode": "560038"},
    {"city": "Bengaluru", "store_name": "Jayanagar",        "address": "11th Main, Jayanagar, Bengaluru",              "pincode": "560041"},
    {"city": "Bengaluru", "store_name": "JP Nagar",         "address": "JP Nagar 2nd Phase, Bengaluru",                "pincode": "560078"},
    {"city": "Bengaluru", "store_name": "Whitefield",       "address": "ITPL Main Road, Whitefield, Bengaluru",        "pincode": "560066"},
    {"city": "Bengaluru", "store_name": "Malleshwaram",     "address": "Margosa Road, Malleshwaram, Bengaluru",        "pincode": "560003"},
    # Pune
    {"city": "Pune", "store_name": "Kalyani Nagar",         "address": "Kalyani Nagar, Pune",                          "pincode": "411006"},
    {"city": "Pune", "store_name": "Aundh",                 "address": "Aundh, Pune",                                  "pincode": "411007"},
    {"city": "Pune", "store_name": "Baner",                 "address": "Baner Road, Pune",                             "pincode": "411045"},
    {"city": "Pune", "store_name": "Viman Nagar",           "address": "Viman Nagar, Pune",                            "pincode": "411014"},
    {"city": "Pune", "store_name": "Kothrud",               "address": "Kothrud, Pune",                                "pincode": "411029"},
    # Kolkata
    {"city": "Kolkata", "store_name": "Park Street",        "address": "Park Street, Kolkata",                         "pincode": "700016"},
    {"city": "Kolkata", "store_name": "Ballygunge",         "address": "Ballygunge Phari, Kolkata",                    "pincode": "700019"},
    {"city": "Kolkata", "store_name": "Salt Lake",          "address": "Sector 1, Salt Lake, Kolkata",                 "pincode": "700064"},
    {"city": "Kolkata", "store_name": "Alipore",            "address": "Alipore, Kolkata",                             "pincode": "700027"},
    {"city": "Kolkata", "store_name": "New Town",           "address": "New Town, Rajarhat, Kolkata",                  "pincode": "700156"},
]

df = pd.DataFrame(STORES)

# Count per pincode
signal8_nb = (
    df.groupby("pincode")
    .size()
    .reset_index(name="natures_basket_count")
    .sort_values("natures_basket_count", ascending=False)
    .reset_index(drop=True)
)

df.to_csv("natures_basket_raw.csv", index=False)
signal8_nb.to_csv("signal8_natures_basket_pincode.csv", index=False)

print(f"✅ Nature's Basket done!")
print(f"   Total stores  : {len(df)}")
print(f"   Unique pincodes: {len(signal8_nb)}")
print(f"\nAll stores by pincode:")
print(signal8_nb)