# ============================================================
# Foodhall + Guardian Pharmacy — Signal 8
# ============================================================

import pandas as pd

# ── Foodhall — only 5 stores across 3 cities ─────────────────
FOODHALL_STORES = [
    {"city": "Mumbai",    "store_name": "Linking Road",      "pincode": "400054"},
    {"city": "Mumbai",    "store_name": "Palladium Mall",    "pincode": "400013"},
    {"city": "Bengaluru", "store_name": "Vittal Mallya Road","pincode": "560001"},
    {"city": "Delhi",     "store_name": "Khan Market",       "pincode": "110003"},
    {"city": "Gurugram",  "store_name": "DLF Cyber Hub",     "pincode": "122002"},
]

# ── Guardian Pharmacy — 63 stores, mainly Delhi NCR ──────────
GUARDIAN_STORES = [
    # Delhi NCR
    {"city": "Delhi",     "store_name": "T3 Terminal IGI",           "pincode": "110037"},
    {"city": "Delhi",     "store_name": "Connaught Place",           "pincode": "110001"},
    {"city": "Delhi",     "store_name": "South Ex",                  "pincode": "110049"},
    {"city": "Delhi",     "store_name": "Lajpat Nagar",              "pincode": "110024"},
    {"city": "Delhi",     "store_name": "Vasant Kunj",               "pincode": "110070"},
    {"city": "Delhi",     "store_name": "Saket",                     "pincode": "110017"},
    {"city": "Delhi",     "store_name": "Rohini",                    "pincode": "110085"},
    {"city": "Delhi",     "store_name": "Janakpuri",                 "pincode": "110058"},
    {"city": "Delhi",     "store_name": "Dwarka",                    "pincode": "110075"},
    {"city": "Delhi",     "store_name": "Preet Vihar",               "pincode": "110092"},
    {"city": "Delhi",     "store_name": "Pitampura",                 "pincode": "110034"},
    {"city": "Delhi",     "store_name": "Rajouri Garden",            "pincode": "110027"},
    {"city": "Gurugram",  "store_name": "Sector 22",                 "pincode": "122001"},
    {"city": "Gurugram",  "store_name": "Sector 14",                 "pincode": "122001"},
    {"city": "Gurugram",  "store_name": "DLF Phase 2",               "pincode": "122022"},
    {"city": "Gurugram",  "store_name": "Sohna Road",                "pincode": "122018"},
    {"city": "Gurugram",  "store_name": "Palam Vihar",               "pincode": "122017"},
    {"city": "Gurugram",  "store_name": "Udyog Vihar HQ",            "pincode": "122008"},
    {"city": "Noida",     "store_name": "Sector 18",                 "pincode": "201301"},
    {"city": "Noida",     "store_name": "Sector 62",                 "pincode": "201309"},
    {"city": "Noida",     "store_name": "Sector 50",                 "pincode": "201301"},
    {"city": "Noida",     "store_name": "Greater Noida",             "pincode": "201310"},
    {"city": "Faridabad", "store_name": "Sector 16",                 "pincode": "121002"},
    {"city": "Faridabad", "store_name": "NIT",                       "pincode": "121001"},
    {"city": "Ghaziabad", "store_name": "Indirapuram",               "pincode": "201014"},
    {"city": "Ghaziabad", "store_name": "Vaishali",                  "pincode": "201010"},
    {"city": "Meerut",    "store_name": "Meerut City",               "pincode": "250001"},
    # Other cities
    {"city": "Mumbai",    "store_name": "Andheri",                   "pincode": "400053"},
    {"city": "Mumbai",    "store_name": "Bandra",                    "pincode": "400050"},
    {"city": "Bengaluru", "store_name": "Koramangala",               "pincode": "560095"},
    {"city": "Bengaluru", "store_name": "Indiranagar",               "pincode": "560038"},
    {"city": "Pune",      "store_name": "Baner",                     "pincode": "411045"},
    {"city": "Pune",      "store_name": "Kalyani Nagar",             "pincode": "411006"},
    {"city": "Jaipur",    "store_name": "Malviya Nagar",             "pincode": "302017"},
    {"city": "Jaipur",    "store_name": "Vaishali Nagar",            "pincode": "302021"},
    {"city": "Lucknow",   "store_name": "Gomti Nagar",               "pincode": "226010"},
    {"city": "Lucknow",   "store_name": "Hazratganj",                "pincode": "226001"},
    {"city": "Chandigarh","store_name": "Sector 17",                 "pincode": "160017"},
    {"city": "Chandigarh","store_name": "Sector 22",                 "pincode": "160022"},
    {"city": "Ludhiana",  "store_name": "Ludhiana City",             "pincode": "141001"},
    {"city": "Agra",      "store_name": "Agra City",                 "pincode": "282001"},
    {"city": "Varanasi",  "store_name": "Varanasi City",             "pincode": "221001"},
    {"city": "Kota",      "store_name": "Kota City",                 "pincode": "324001"},
    {"city": "Ranchi",    "store_name": "Ranchi City",               "pincode": "834001"},
    {"city": "Surat",     "store_name": "Surat City",                "pincode": "395001"},
    {"city": "Vadodara",  "store_name": "Vadodara City",             "pincode": "390001"},
]

# ── Process Foodhall ──────────────────────────────────────────
df_fh = pd.DataFrame(FOODHALL_STORES)
df_fh["brand"] = "Foodhall"

signal8_fh = (
    df_fh.groupby("pincode")
    .size()
    .reset_index(name="foodhall_count")
    .sort_values("foodhall_count", ascending=False)
    .reset_index(drop=True)
)

df_fh.to_csv("foodhall_raw.csv", index=False)
signal8_fh.to_csv("signal8_foodhall_pincode.csv", index=False)

print(f"✅ Foodhall done!")
print(f"   Total stores   : {len(df_fh)}")
print(f"   Unique pincodes: {len(signal8_fh)}")

# ── Process Guardian ──────────────────────────────────────────
df_gd = pd.DataFrame(GUARDIAN_STORES)
df_gd["brand"] = "Guardian"

signal8_gd = (
    df_gd.groupby("pincode")
    .size()
    .reset_index(name="guardian_count")
    .sort_values("guardian_count", ascending=False)
    .reset_index(drop=True)
)

df_gd.to_csv("guardian_raw.csv", index=False)
signal8_gd.to_csv("signal8_guardian_pincode.csv", index=False)

print(f"\n✅ Guardian Pharmacy done!")
print(f"   Total stores   : {len(df_gd)}")
print(f"   Unique pincodes: {len(signal8_gd)}")

# ── Combine all 4 brands ──────────────────────────────────────
# Load Apollo and Nature's Basket CSVs + add brand column
df_apollo = pd.read_csv("apollo_stores_raw_fixed.csv")
# Convert pincode to string and drop the dirty dummy pincode 117050
df_apollo["pincode"] = df_apollo["pincode"].astype(str).str.replace(r"\.0$", "", regex=True)
df_apollo = df_apollo[df_apollo["pincode"] != "117050"]
df_apollo["brand"] = "Apollo Pharmacy"

df_nb = pd.read_csv("natures_basket_raw.csv")
df_nb["brand"] = "Natures Basket"

# Combine all
df_all = pd.concat([
    df_apollo[["brand", "store_name", "pincode"]],
    df_nb[["brand", "store_name", "pincode"]],
    df_fh[["brand", "store_name", "pincode"]],
    df_gd[["brand", "store_name", "pincode"]],
], ignore_index=True)

# Final Signal 8 — total premium store count per pincode
signal8_final = (
    df_all.groupby("pincode")
    .size()
    .reset_index(name="premium_store_count")
    .sort_values("premium_store_count", ascending=False)
    .reset_index(drop=True)
)

df_all.to_csv("signal8_all_brands_raw.csv", index=False)
signal8_final.to_csv("signal8_final_pincode.csv", index=False)

print(f"\n{'='*50}")
print(f"✅ SIGNAL 8 COMPLETE — All 4 brands combined!")
print(f"   Apollo Pharmacy : {len(df_apollo)} stores")
print(f"   Natures Basket  : {len(df_nb)} stores")
print(f"   Foodhall        : {len(df_fh)} stores")
print(f"   Guardian        : {len(df_gd)} stores")
print(f"   Total stores    : {len(df_all)}")
print(f"   Unique pincodes : {len(signal8_final)}")
print(f"\nTop 10 pincodes by premium store density:")
print(signal8_final.head(10))