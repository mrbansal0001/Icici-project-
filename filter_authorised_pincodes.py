"""
filter_authorised_pincodes.py
Removes pincodes from final_master_dataset.csv that are NOT in the official
India Post authorised pincode list.
"""
import pandas as pd, shutil

MASTER = "/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset.csv"
AUTH   = "/Users/tanishbansal/Library/CloudStorage/OneDrive-IITKanpur/Downloads/authorised_pincode_list.csv"
BACKUP = MASTER.replace(".csv", "_backup_prefilter.csv")

master = pd.read_csv(MASTER)
auth   = pd.read_csv(AUTH)

print(f"Master rows before filter : {len(master):,}")

auth_pins = set(auth["pincode"].dropna().astype(int).unique())
print(f"Authorised unique pincodes: {len(auth_pins):,}")

shutil.copy(MASTER, BACKUP)
print(f"Backup saved → {BACKUP}")

master["pincode"] = master["pincode"].astype(int)
filtered = master[master["pincode"].isin(auth_pins)].copy()

removed = len(master) - len(filtered)
print(f"Rows removed              : {removed:,}")
print(f"Master rows after filter  : {len(filtered):,}")

filtered.to_csv(MASTER, index=False)
print(f"\n✅  Saved filtered dataset → {MASTER}")
