import pandas as pd
from numbers_parser import Document

def clean_pincode(series):
    return series.astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

print("Loading final_master_dataset_v2.numbers...")
doc = Document('/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset_v2.numbers')
data = doc.sheets[0].tables[0].rows(values_only=True)
df = pd.DataFrame(data[1:], columns=data[0])

# Clean pincode
df['pincode'] = clean_pincode(df['pincode'])

# Load missing schools data
print("Loading missing_school_counts.csv...")
missing_df = pd.read_csv('/Users/tanishbansal/Downloads/soham data/missing_school_counts.csv')
missing_df['pincode'] = clean_pincode(missing_df['pincode'])

# Create a dictionary for quick mapping
missing_map = dict(zip(missing_df['pincode'], missing_df['school_counts']))

# Update the distributed_school_count
count_updated = 0
for i, row in df.iterrows():
    pin = row['pincode']
    if pin in missing_map:
        if pd.isna(row['distributed_school_count']) or float(row['distributed_school_count']) == 0:
            df.at[i, 'distributed_school_count'] = missing_map[pin]
            count_updated += 1

print(f"Successfully updated {count_updated} pincodes with their missing school counts!")

output_path = '/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset_v3.csv'
df.to_csv(output_path, index=False)
print(f"Saved to {output_path}")
