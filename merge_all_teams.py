import pandas as pd
import os

# Paths to the three final datasets
path_parv = "/Users/tanishbansal/Downloads/parv data /merged_parv_signals.csv"
path_soham = "/Users/tanishbansal/Downloads/soham data/merged_soham_signals.csv"
path_tanish = "/Users/tanishbansal/Library/CloudStorage/GoogleDrive-bansaltanish8935@gmail.com/My Drive/icic bank project/master_output/final_merged_678.csv"

print("Loading files...")
df_parv = pd.read_csv(path_parv)
df_soham = pd.read_csv(path_soham)
df_tanish = pd.read_csv(path_tanish)

# Standardize the pincode format across all datasets
for df in [df_parv, df_soham, df_tanish]:
    df["pincode"] = df["pincode"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    df.drop_duplicates(subset=["pincode"], inplace=True)

print("Merging Tanish (678) + Parv...")
master = pd.merge(df_tanish, df_parv, on="pincode", how="outer")

print("Merging Master + Soham...")
master = pd.merge(master, df_soham, on="pincode", how="outer")

print("Cleaning up missing values...")
master.fillna(0, inplace=True)

# Convert all metrics to integers except for ratios
for col in master.columns:
    if col != "pincode" and "ratio" not in col.lower():
        master[col] = master[col].astype(int)

# Sort strictly by pincode
master.sort_values("pincode", inplace=True)

out_file = "/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset.csv"
master.to_csv(out_file, index=False)

print(f"\n✅ Master merge successful! Saved to: {out_file}")
print(f"   Total unique pincodes combined: {len(master)}")
print(f"   Total columns (signals): {len(master.columns)}")
print(f"   Columns: {list(master.columns)}")
