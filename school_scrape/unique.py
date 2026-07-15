import pandas as pd

# 1. Load the three CSV files
df1 = pd.read_csv(r"C:\Users\soham\Desktop\icici\scrape\output\schools.csv", low_memory=False)
df2 = pd.read_csv(r"C:\Users\soham\Desktop\icici\scrape\output\schools_parallel.csv", low_memory=False)
df3 = pd.read_csv(r"C:\Users\soham\Desktop\icici\scrape\output\schools_parallel2.csv", low_memory=False)

# 2. Combine them into a single DataFrame
df = pd.concat([df1, df2, df3], ignore_index=True)

# 3. Extract unique values
# .dropna() ensures we don't print "nan" (blank cells) if there are any
# sorted() arranges them alphabetically so they are easier to read
unique_types = sorted(df['schMgmtType'].dropna().unique())

# 4. Print the results
print(f"Total unique management types found: {len(unique_types)}\n")
print("List of Unique Types:")
print("-" * 30)

for mgmt_type in unique_types:
    print(f"- {mgmt_type}")