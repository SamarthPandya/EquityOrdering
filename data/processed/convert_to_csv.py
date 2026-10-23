import pandas as pd
import os

# 1. Provide your file name right here
file_name = "data/processed/clean_options_chain.parquet"  # Replace with your actual file name

if os.path.exists(file_name):
    print(f"Loading {file_name}...")
    
    # 2. Read the .parquet file into a DataFrame
    df = pd.read_parquet(file_name)
    
    # 3. Create the .csv file name automatically
    csv_file_name = file_name.replace('.parquet', '.csv')
    
    # 4. Save to CSV in the same directory without the index column
    df.to_csv(csv_file_name, index=False)
    
    print(f"Success! Converted file saved as: {csv_file_name}")
else:
    print(f"Error: Could not find '{file_name}' in the current directory.")