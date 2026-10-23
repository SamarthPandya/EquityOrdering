import os
import pandas as pd
import datetime

def check_file(path):
    if os.path.exists(path):
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        print(f"[{mtime.strftime('%H:%M:%S')}] {path}")
    else:
        print(f"[MISSING] {path}")

print("--- 1. FILE TIMESTAMPS ---")
check_file("data/processed/clean_options_chain_v2.parquet")
check_file("data/processed/monthly_skew_signals_v2_delta.parquet")

print("\n--- 2. DELTA TARGET CHECK ---")
try:
    df = pd.read_parquet("data/processed/clean_options_chain_v2.parquet")
    ce_delta = df[df['OPT_TYPE'] == 'CE']['DELTA'].mean()
    pe_delta = df[df['OPT_TYPE'] == 'PE']['DELTA'].mean()
    print(f"Average CE Delta: {ce_delta:.4f} (We want ~0.50)")
    print(f"Average PE Delta: {pe_delta:.4f} (We want ~-0.10)")
except Exception as e:
    print(f"Failed to load options data: {e}")

print("\n--- 3. SIGNAL INTEGRITY ---")
try:
    sig = pd.read_parquet("data/processed/monthly_skew_signals_v2_delta.parquet")
    print(f"Total valid signal rows: {len(sig)}")
    print(f"Missing SKEW_EMA values: {sig['SKEW_EMA'].isna().sum()}")
except Exception as e:
    print(f"Failed to load signal data: {e}")