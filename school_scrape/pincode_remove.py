import pandas as pd

# 1. Define data types as strings to ensure perfect matching
dtypes = {'pincode': str}

# 2. Load the two CSV files
schools_df = pd.read_csv(r"C:\Users\soham\Desktop\icici\scrape\5c2f62fe-5afa-4119-a499-fec9d604d5bd.csv", dtype=dtypes)
my_pincodes_df = pd.read_csv(r"C:\Users\soham\Desktop\icici\scrape\pincodes.csv", dtype=dtypes)

# 3. Create a list of the valid pincodes from the schools file
valid_pincodes = schools_df['pincode'].unique()

# 4. Find the EXCLUDED pincodes
# The tilde (~) means "NOT". This keeps rows where the pincode is NOT in the valid list.
excluded_pincodes_df = my_pincodes_df[~my_pincodes_df['pincode'].isin(valid_pincodes)]

# 5. Save the result
excluded_pincodes_df.to_csv(r"C:\Users\soham\Desktop\icici\scrape\excluded_pincodes.csv", index=False)

print(f"Total pincodes in your original file: {len(my_pincodes_df)}")
print(f"Pincodes that were excluded (not found in schools): {len(excluded_pincodes_df)}")
print("Processing complete. Saved as 'excluded_pincodes.csv'.")