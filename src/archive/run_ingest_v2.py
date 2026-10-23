import os
import glob
from archive.ingestion_v2 import process_bhavcopy_batch_v2

def main():
    # 1. Point to your folder containing the raw NSE CSV files
    raw_data_folder = "data/raw_fo"  # Update this path if your CSVs are stored elsewhere
    
    # Grab all CSV files in the directory
    csv_files = glob.glob(os.path.join(raw_data_folder, "*.csv"))
    
    if not csv_files:
        print("No CSV files found. Please check your data directory.")
        return
        
    print(f"Found {len(csv_files)} Bhavcopy files. Starting Delta-based V2 ingestion...")
    print("Note: This will take longer than V1 because the Black-76 solver is running row-by-row.")
    
    # 2. Call the batch processor
    clean_df = process_bhavcopy_batch_v2(csv_files)
    
    # 3. Save to Parquet
    if not clean_df.empty:
        os.makedirs("data/processed", exist_ok=True)
        output_path = "data/processed/clean_options_chain_v2.parquet"
        clean_df.to_parquet(output_path, index=False)
        print(f"\nSuccess! Filtered Delta-matched data saved to: {output_path}")
        print(f"Total rows generated: {len(clean_df)}")
        print(clean_df[['DATE', 'SYMBOL', 'OPT_TYPE', 'STRIKE', 'DELTA', 'IV']].head(10))
    else:
        print("Ingestion resulted in an empty DataFrame. Check your raw files and filters.")

if __name__ == "__main__":
    main()