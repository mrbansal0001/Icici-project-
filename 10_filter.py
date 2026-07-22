import pandas as pd

# 1. Load the three CSV files
# df1 = pd.read_csv(r"C:\Users\soham\Desktop\icici\scrape\output\schools.csv", low_memory=False)
# df2 = pd.read_csv(r"C:\Users\soham\Desktop\icici\scrape\output\schools_parallel.csv", low_memory=False)
# df3 = pd.read_csv(r"C:\Users\soham\Desktop\icici\scrape\output\schools_parallel2.csv", low_memory=False)
df4 = pd.read_csv(r"C:\Users\soham\Desktop\icici\scrape\output\missing_schools.csv", low_memory=False)

# 2. Combine them into a single DataFrame
df = pd.concat([df4], ignore_index=True)

# 3. Remove duplicate COLUMNS (keeps only the first column if there are identical headers)
df = df.loc[:, ~df.columns.duplicated()]

# 4. Remove duplicate ROWS (highly recommended for parallel scrapes!)
# We use 'udiseschCode' because it is a unique identifier for each school.
# This ensures that if the same school is in df1 and df2, it only gets counted once.
df = df.drop_duplicates(subset=['udiseschCode'])

# Create a list of the exact exact categories you want to REMOVE
govt_categories = [
    'Central Tibetan School',
    'Department of Education',
    'Government Aided',
    'Jawahar Navodaya Vidyalaya ', # Note: check if there is a trailing space in your data!
    'Kendriya Vidyalaya / Central School',
    'Local body',
    'Ministry of Labor',
    'Other Central Govt. Schools',
    'Other Govt. managed schools',
    'Railway School',
    'Sainik School',
    'Social welfare Department',
    'Tribal Welfare Department'
]

# Filter OUT any row where the schMgmtType is IN that list
# The ~ symbol still means "NOT"
filtered_df = df[~df['schMgmtType'].isin(govt_categories)]

# 6. Group by 'pincode' and count the number of schools in each
pincode_counts = filtered_df.groupby('pincode').size().reset_index(name='school_counts')

# 7. Save the result to a new CSV file
pincode_counts.to_csv('missing_school_counts.csv', index=False)

print("Processing complete. The results have been saved to 'missing_school_counts.csv'.")