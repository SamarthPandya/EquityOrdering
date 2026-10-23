import os
import pandas as pd
import numpy as np

# Revert to your original signal generator
from archive.signal_v2 import build_monthly_skew_signal_v2
from archive.backtest_v2 import run_cross_sectional_backtest_v2

def main():
    print("Loading 50-Delta/10-Delta matched options data...")
    clean_df = pd.read_parquet("data/processed/clean_options_chain_v2.parquet")
    
    print("Computing Smoothed Skew via original solver...")
    # This implicit filter is what cleans the data for the EMA
    monthly_skew_v2 = build_monthly_skew_signal_v2(clean_df)
    
    signal_output_path = "data/processed/monthly_skew_signals_v2.parquet"
    monthly_skew_v2.to_parquet(signal_output_path, index=False)
    
    print("Loading existing adjusted equity closes...")
    prices = pd.read_parquet("data/processed/equity_adj_closes.parquet")
    signals = pd.read_parquet(signal_output_path)
    
    signals['REBAL_DATE'] = pd.to_datetime(signals['REBAL_DATE'])
    prices['DATE'] = pd.to_datetime(prices['DATE'])
    
    print("Running V2 Cross-Sectional Backtest...")
    results = run_cross_sectional_backtest_v2(signals, prices)
    
    rets = results['bucket_returns']
    ic = results['ic']
    turnover = results['turnover']

    print("\n--- VERSION 2: ANNUALIZED BACKTEST RESULTS ---")
    months = len(rets)
    print(f"Total Months Tested: {months}")

    ann_ret = (1 + rets.mean()) ** 12 - 1

    print("\nAnnualized Returns by Quintile:")
    for q in [1, 2, 3, 4, 5]:
        if q in ann_ret:
            print(f"Q{q}: {ann_ret[q]:.2%}")
            
    print(f"Universe (EW): {ann_ret['EW_UNIVERSE']:.2%}")
    print(f"Long-Only Active (Q1 - EW): {ann_ret['Q1_MINUS_EW']:.2%}")
    print(f"Long/Short Spread (Q1 - Q5): {ann_ret['Q1_MINUS_Q5']:.2%}")

    print("\n--- VERSION 2: SIGNAL METRICS ---")
    print(f"Mean Rank IC: {ic.mean():.4f}")
    print(f"IC IR (Annualized): {(ic.mean() / ic.std()) * np.sqrt(12):.4f}")
    print(f"Average Q1 Monthly Turnover: {turnover.mean():.2%}")

if __name__ == "__main__":
    main()