"""
build_dashboard.py
──────────────────
Reads final_master_dataset_scored_v2.csv, builds the JSON PAYLOAD
(states, rows, stateSummary, mapPaths), and injects it into the
existing HTML template, replacing the old PAYLOAD.

Output: /Users/tanishbansal/Library/CloudStorage/OneDrive-IITKanpur/Downloads/pincode_affluence_dashboard.html
"""
import pandas as pd
import json
import re

SCORED  = "/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset_scored_v2.csv"
AUTH    = "/Users/tanishbansal/Library/CloudStorage/OneDrive-IITKanpur/Downloads/authorised_pincode_list.csv"
HTML_IN = "/Users/tanishbansal/Projects/icici_bank_signals/dashboard_template.html"
HTML_OUT = "/Users/tanishbansal/Projects/icici_bank_signals/pincode_affluence_dashboard_v2.html"

# ── 1. Load data ──────────────────────────────────────────────────────────
df = pd.read_csv(SCORED)
auth = pd.read_csv(AUTH)

print(f"Scored rows: {len(df):,}")

# ── 2. Build pincode → state mapping from authorised list ─────────────────
# Take first occurrence per pincode (unique mapping)
pin_state = (
    auth[["pincode", "statename"]]
    .drop_duplicates(subset="pincode")
    .copy()
)
pin_state["pincode"] = pin_state["pincode"].astype(int)
pin_state["statename"] = (
    pin_state["statename"]
    .str.strip()
    .str.title()
    .str.replace(r"\s+", " ", regex=True)
)

df["pincode"] = df["pincode"].astype(int)
df = df.merge(pin_state, on="pincode", how="left")
df["statename"] = df["statename"].fillna("Unknown")

# ── 3. Build sorted states index ──────────────────────────────────────────
states_list = sorted(df["statename"].unique().tolist())
state_to_idx = {s: i for i, s in enumerate(states_list)}
print(f"Unique states: {len(states_list)}")

# ── 4. Tier → compact code ────────────────────────────────────────────────
TIER_MAP = {"Platinum": "P", "Gold": "G", "Silver": "S", "Standard": "N"}

# ── 5. Build rows array ───────────────────────────────────────────────────
rows = []
for _, r in df.iterrows():
    tier = TIER_MAP.get(r["Affluence_Tier"], "N")
    row = {
        "p":   int(r["pincode"]),
        "s":   state_to_idx.get(r["statename"], 0),
        "sc":  round(float(r["Affluence_Score"]), 2),
        "t":   tier,
        "fp":  round(float(r["Financial_Penetration"]),   2),
        "cv":  round(float(r["Commercial_Vibrancy"]),     2),
        "lp":  round(float(r["Lifestyle_Premium"]),       2),
        "inf": round(float(r["Infrastructure_Scale"]),    2),
        # raw signals (compact)
        "mf":  int(r.get("MF_Distributor_Count", 0)),
        "ia":  int(r.get("Investment_Advisor_Count", 0)),
        "ch":  int(r.get("Total_Corporate_Hubs", 0)),
        "rb":  int(r.get("Total_Retail_Branches", 0)),
        "rr":  round(float(r.get("Retail_Private_to_Public_Ratio", 0)), 2),
        "ps":  int(r.get("premium_store_count", 0)),
        "gc":  int(r.get("Golf_Course_Count", 0)),
        "hc":  int(r.get("nabh_hospital_count", 0)),
        "ev":  int(r.get("ev_charging_station_count", 0)),
        "vc":  int(r.get("distributed_vehicle_count", 0)),
        "sch": int(r.get("distributed_school_count", 0)),
        "est": int(r.get("establishment_count", 0)),
    }
    rows.append(row)

# Sort by score descending
rows.sort(key=lambda x: -x["sc"])
print(f"Rows built: {len(rows):,}")

# ── 6. Build stateSummary ─────────────────────────────────────────────────
summary = []
for state in states_list:
    sub = df[df["statename"] == state]
    total = len(sub)
    plat  = int((sub["Affluence_Tier"] == "Platinum").sum())
    gold  = int((sub["Affluence_Tier"] == "Gold").sum())
    silv  = int((sub["Affluence_Tier"] == "Silver").sum())
    std   = int((sub["Affluence_Tier"] == "Standard").sum())
    avg   = round(float(sub["Affluence_Score"].mean()), 2)
    plat_pct = round(plat / total * 100, 2) if total > 0 else 0.0
    summary.append({
        "state":          state,
        "total_pincodes": total,
        "avg_score":      avg,
        "platinum":       plat,
        "gold":           gold,
        "silver":         silv,
        "standard":       std,
        "platinum_pct":   plat_pct,
    })

# ── 7. Extract mapPaths from existing HTML (reuse — map paths don't change) ─
with open(HTML_IN, "r", encoding="utf-8") as f:
    html = f.read()

idx_start = html.find('const PAYLOAD = ')
payload_start = idx_start + len('const PAYLOAD = ')
idx_end = html.find(';\n', payload_start)
old_payload_str = html[payload_start:idx_end]

try:
    old_payload = json.loads(old_payload_str)
    map_paths = old_payload["mapPaths"]
    print(f"Reused mapPaths: {len(map_paths['paths'])} state paths")
except Exception as e:
    print(f"⚠️  Could not parse old mapPaths: {e}")
    map_paths = {"viewW": 800, "viewH": 900, "paths": []}

# ── 8. Assemble new PAYLOAD ───────────────────────────────────────────────
new_payload = {
    "states":       states_list,
    "rows":         rows,
    "stateSummary": summary,
    "mapPaths":     map_paths,
}

payload_json = json.dumps(new_payload, separators=(",", ":"), ensure_ascii=False)
print(f"PAYLOAD JSON size: {len(payload_json)/1024/1024:.1f} MB")

# ── 9. Replace old PAYLOAD in HTML ────────────────────────────────────────
new_html = html[:payload_start] + payload_json + html[idx_end:]

with open(HTML_OUT, "w", encoding="utf-8") as f:
    f.write(new_html)

print(f"\n✅  Dashboard updated → {HTML_OUT}")
print(f"   Total pincodes in dashboard: {len(rows):,}")
