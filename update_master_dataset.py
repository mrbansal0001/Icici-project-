import pandas as pd
from numbers_parser import Document
import os

def clean_pincode(series):
    return series.astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

def main():
    # 1. Load Master Dataset
    master_path = '/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset.csv'
    df_master = pd.read_csv(master_path)
    df_master['pincode'] = clean_pincode(df_master['pincode'])
    
    # 2. Load Soham Data
    soham_path = '/Users/tanishbansal/Downloads/soham data/pincode_school_counts.numbers'
    doc = Document(soham_path)
    data = doc.sheets[0].tables[0].rows(values_only=True)
    df_soham = pd.DataFrame(data[1:], columns=data[0])
    df_soham.rename(columns={'school_counts': 'distributed_school_count'}, inplace=True)
    df_soham['pincode'] = clean_pincode(df_soham['pincode'])
    
    # 3. Load Parv Data
    parv_path = '/Users/tanishbansal/Downloads/parv data /FINAL_19586_FEATURES.csv'
    df_parv = pd.read_csv(parv_path)
    df_parv.rename(columns={'Pincode': 'pincode'}, inplace=True)
    df_parv['pincode'] = clean_pincode(df_parv['pincode'])
    
    # Select specific Parv columns
    parv_cols = [
        'pincode', 'Total_Retail_Branches', 'Total_Corporate_Hubs', 
        'Private_Retail', 'Public_Retail', 'Retail_Private_to_Public_Ratio', 
        'MF_Distributor_Count', 'Investment_Advisor_Count', 'Golf_Course_Count', 
        'Total_Financial_Infrastructure'
    ]
    df_parv = df_parv[parv_cols]
    
    # 4. Identify Mismatched Pincodes for Reporting
    master_pins = set(df_master['pincode'].unique())
    soham_pins = set(df_soham['pincode'].unique())
    parv_pins = set(df_parv['pincode'].unique())
    
    soham_missing_in_master = soham_pins - master_pins
    parv_missing_in_master = parv_pins - master_pins
    master_missing_in_soham = master_pins - soham_pins
    master_missing_in_parv = master_pins - parv_pins
    
    # Export mismatch reports for user
    with open("mismatch_report.txt", "w") as f:
        f.write(f"Soham pincodes not in Master (Ignored due to Left Join): {len(soham_missing_in_master)}\n")
        f.write(f"Parv pincodes not in Master (Ignored due to Left Join): {len(parv_missing_in_master)}\n\n")
        
        f.write(f"Master pincodes missing in Soham data (Filled with 0): {len(master_missing_in_soham)}\n")
        f.write(f"{','.join(list(master_missing_in_soham))}\n\n")
        
        f.write(f"Master pincodes missing in Parv data (Filled with 0): {len(master_missing_in_parv)}\n")
        f.write(f"{','.join(list(master_missing_in_parv))}\n")

    # 5. Drop outdated columns from Master
    cols_to_drop = [
        'distributed_school_count', 'Total_Retail_Branches', 'Total_Corporate_Hubs',
        'Retail_Private_to_Public_Ratio', 'MF_Distributor_Count', 
        'Investment_Advisor_Count', 'Golf_Course_Count'
    ]
    df_master = df_master.drop(columns=[c for c in cols_to_drop if c in df_master.columns])
    
    # 6. Left Join
    df_master = pd.merge(df_master, df_soham, on='pincode', how='left')
    df_master = pd.merge(df_master, df_parv, on='pincode', how='left')
    
    # 7. Fill NAs with 0
    numeric_cols = df_master.select_dtypes(include=['float64', 'int64']).columns
    df_master[numeric_cols] = df_master[numeric_cols].fillna(0)
    
    # Soham's column might have come in as object if there were NAs originally, let's coerce and fill
    df_master['distributed_school_count'] = pd.to_numeric(df_master['distributed_school_count'], errors='coerce').fillna(0).astype(int)
    
    # Ensure all original columns + updated columns are integer where appropriate
    for col in cols_to_drop + ['Private_Retail', 'Public_Retail', 'Total_Financial_Infrastructure']:
        if col in df_master.columns:
            if col != 'Retail_Private_to_Public_Ratio':
                df_master[col] = pd.to_numeric(df_master[col], errors='coerce').fillna(0).astype(int)
            else:
                df_master[col] = pd.to_numeric(df_master[col], errors='coerce').fillna(0.0)

    # 8. Save
    output_path = '/Users/tanishbansal/Projects/icici_bank_signals/final_master_dataset_v2.csv'
    df_master.to_csv(output_path, index=False)
    print("Done! Saved to", output_path)

if __name__ == "__main__":
    main()
