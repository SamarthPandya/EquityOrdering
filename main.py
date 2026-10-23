import os
import pandas as pd
from src.signal import build_monthly_skew_signal
from fetchStockData import fetch_forward_returns # Or whatever you named your fetch file
from src.backtest import run_cross_sectional_backtest

# ... (Steps 1 to 4: Ingestion) ...

# 5. Load the clean parquet and compute the Skew signal
print("Computing Implied Volatilities and Monthly Skew...")
clean_df = pd.read_parquet("data/processed/clean_options_chain.parquet")
monthly_skew = build_monthly_skew_signal(clean_df)
monthly_skew.to_parquet("data/processed/monthly_skew_signals_smoothed.parquet", index=False)

# 5.5 Fetch Adjusted Returns from yfinance
price_file = "data/processed/equity_adj_closes.parquet"
if not os.path.exists(price_file):
    print("Price file not found. Fetching adjusted equity closes...")
    prices = fetch_forward_returns(monthly_skew)
else:
    print("Loading existing adjusted equity closes...")
    prices = pd.read_parquet(price_file)

# 6. Run the Backtest
print("Running Cross-Sectional Backtest...")
signals = pd.read_parquet("data/processed/monthly_skew_signals_smoothed.parquet")

# Ensure datatypes align
signals['REBAL_DATE'] = pd.to_datetime(signals['REBAL_DATE'])
prices['DATE'] = pd.to_datetime(prices['DATE'])

results = run_cross_sectional_backtest(signals, prices)

# 7. Print Summary Statistics for the Deliverable
rets = results['bucket_returns']
ic = results['ic']
turnover = results['turnover']

import numpy as np

print("\n--- ANNUALIZED BACKTEST RESULTS ---")
months = len(rets)
print(f"Total Months Tested: {months}")

# Annualized returns (assuming 12 months/year)
ann_ret = (1 + rets.mean()) ** 12 - 1

print("\nAnnualized Returns by Quintile:")
for q in [1, 2, 3, 4, 5]:
    if q in ann_ret:
        print(f"Q{q}: {ann_ret[q]:.2%}")
        
print(f"Universe (EW): {ann_ret['EW_UNIVERSE']:.2%}")
print(f"Long-Only Active (Q1 - EW): {ann_ret['Q1_MINUS_EW']:.2%}")
print(f"Long/Short Spread (Q1 - Q5): {ann_ret['Q1_MINUS_Q5']:.2%}")

print("\n--- SIGNAL METRICS ---")
print(f"Mean Rank IC: {ic.mean():.4f}")
print(f"IC IR (Annualized): {(ic.mean() / ic.std()) * np.sqrt(12):.4f}")
print(f"Average Q1 Monthly Turnover: {turnover.mean():.2%}")