import pandas as pd
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# 1. Define your file path
file_path = BASE_DIR / 'udise-schools-all.csv'

if os.path.exists(file_path):
    # 2. Load the CSV into a pandas DataFrame
    df = pd.read_csv(file_path)
    
    # 3. Filter out 'government' schools
    # The ~ symbol acts as a "NOT" operator to exclude these rows.
    # case=False ensures it catches variations like 'Government' or 'GOVERNMENT'.
    # na=False prevents errors if there are empty cells in the column.
    df_filtered = df[~df['Management'].str.contains('Government|Central Govt', case=False, na=False)]
    
    # Optional: See how many rows were dropped
    print(f"Original row count: {len(df)}")
    print(f"Filtered row count (non-government): {len(df_filtered)}")
    
    # 4. Group by PIN Code and count the schools
    # Using 'UDISE Code' to count since it's a unique identifier for each school
    school_counts = df_filtered.groupby('PIN Code')['UDISE Code'].count().reset_index()
    
    # Rename the columns for a cleaner output
    school_counts.columns = ['PIN Code', 'Non_Gov_School_Count']
    
    # 5. Display the results
    print("\n--- Non-Government School Counts by PIN Code ---")
    print(school_counts.head())
    
    # 6. Save the results to the working directory
    output_path = BASE_DIR / 'school_counts.csv'
    school_counts.to_csv(output_path, index=False)
    print(f"\nSuccess! Grouped data saved to: {output_path}")

else:
    print(f"Error: Could not find the file at {file_path}. Please check the path.")