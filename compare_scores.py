import pandas as pd
import numpy as np

# Load both datasets
df_old = pd.read_csv('/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset_scored.csv', dtype={'pincode': str})
df_new = pd.read_csv('/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset_scored_v2.csv', dtype={'pincode': str})

# Standardize pincodes
df_old['pincode'] = df_old['pincode'].str.replace(r"\.0$", "", regex=True).str.strip()
df_new['pincode'] = df_new['pincode'].str.replace(r"\.0$", "", regex=True).str.strip()

# Merge on pincode
df_merged = pd.merge(
    df_old[['pincode', 'Affluence_Score', 'Affluence_Tier']],
    df_new[['pincode', 'Affluence_Score', 'Affluence_Tier']],
    on='pincode',
    suffixes=('_old', '_new')
)

print("--- OVERALL COMPARISON ---")
print(f"Total pincodes compared: {len(df_merged)}")

score_diff = df_merged['Affluence_Score_new'] - df_merged['Affluence_Score_old']
print(f"Mean Score Shift: {score_diff.mean():.2f}")
print(f"Median Score Shift: {score_diff.median():.2f}")
print(f"Max Positive Shift: {score_diff.max():.2f}")
print(f"Max Negative Shift: {score_diff.min():.2f}")

print("\n--- TIER SHIFTS ---")
tier_order = {"Standard": 1, "Silver": 2, "Gold": 3, "Platinum": 4}
df_merged['tier_num_old'] = df_merged['Affluence_Tier_old'].map(tier_order)
df_merged['tier_num_new'] = df_merged['Affluence_Tier_new'].map(tier_order)

promoted = df_merged[df_merged['tier_num_new'] > df_merged['tier_num_old']]
demoted = df_merged[df_merged['tier_num_new'] < df_merged['tier_num_old']]
unchanged = df_merged[df_merged['tier_num_new'] == df_merged['tier_num_old']]

print(f"Pincodes Promoted to a higher tier: {len(promoted)}")
print(f"Pincodes Demoted to a lower tier: {len(demoted)}")
print(f"Pincodes Unchanged: {len(unchanged)}")

print("\n--- KNOWN BENCHMARK PINCODES ---")
KNOWN_PINCODES = {
    "560001": "Bangalore - MG Road (High)",
    "122002": "Gurgaon - DLF City (High)",
    "110001": "Delhi - Connaught Place (High)",
    "400026": "Mumbai - Worli (High)",
    "500034": "Hyderabad - Banjara Hills (High)",
    "845401": "Rural Bihar (Low)",
    "262401": "Rural Uttarakhand (Low)",
    "752101": "Rural Odisha (Low)",
}

for pin, desc in KNOWN_PINCODES.items():
    row = df_merged[df_merged['pincode'] == pin]
    if not row.empty:
        old_score = row.iloc[0]['Affluence_Score_old']
        new_score = row.iloc[0]['Affluence_Score_new']
        diff = new_score - old_score
        print(f"{desc} ({pin}): Old={old_score:.1f} -> New={new_score:.1f} (Shift: {diff:+.1f})")

