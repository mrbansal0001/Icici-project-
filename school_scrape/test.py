import pandas as pd

# 1. Define file paths (Change these to match your exact setup)
report_file_path = r"C:\Users\soham\Desktop\icici\scrape\mismatch_report.txt"
pincodes_csv_path = r"C:\Users\soham\Desktop\icici\scrape\pincodes.csv"
output_missing_path = r"C:\Users\soham\Desktop\icici\scrape\truly_missing_pincodes.csv"

# ---------------------------------------------------------
# STEP 1: Extract pincodes from the text report
# ---------------------------------------------------------
report_pincodes = []

with open(report_file_path, 'r') as file:
    lines = file.readlines()

for i, line in enumerate(lines):
    if "Master pincodes missing in Soham data" in line:
        # The comma-separated list is on the very next line
        pincodes_string = lines[i + 1].strip()
        
        # Split by comma and clean up any accidental spaces
        report_pincodes = [p.strip() for p in pincodes_string.split(',')]
        break

# Convert to a Python 'set' for lightning-fast comparison
report_pincodes_set = set(report_pincodes)

# ---------------------------------------------------------
# STEP 2: Extract pincodes from your CSV
# ---------------------------------------------------------
# Load the CSV, forcing the pincode column to be strings
csv_df = pd.read_csv(pincodes_csv_path, dtype={'pincode': str})

# Drop any blank rows and convert the unique pincodes to a set
csv_pincodes_set = set(csv_df['pincode'].dropna().unique())

# ---------------------------------------------------------
# STEP 3: Compare the two lists
# ---------------------------------------------------------
# Subtracting the sets finds items in the report that are NOT in the CSV
truly_missing = report_pincodes_set - csv_pincodes_set

# ---------------------------------------------------------
# STEP 4: Save the results
# ---------------------------------------------------------
# Convert back to a DataFrame to save as CSV
truly_missing_df = pd.DataFrame({'pincode': list(truly_missing)})
truly_missing_df.to_csv(output_missing_path, index=False)

print(f"Unique pincodes found in report: {len(report_pincodes_set)}")
print(f"Unique pincodes found in CSV: {len(csv_pincodes_set)}")
print("-" * 40)
print(f"Pincodes from the report MISSING from the CSV: {len(truly_missing)}")
print(f"List saved to: {output_missing_path}")