import pandas as pd
import numpy as np
from archive.signal_v2 import build_smoothed_moneyness_signal
from archive.backtest_v2 import run_cross_sectional_backtest_v2

def main():
    print("Loading Simple Moneyness options data...")
    # Make sure this points to your original V1 ingestion file, NOT the _v2 Delta file
    clean_df = pd.read_parquet("data/processed/clean_options_chain.parquet") 
    
    print("Computing Smoothed Moneyness Skew...")
    monthly_skew = build_smoothed_moneyness_signal(clean_df)
    
    signal_output_path = "data/processed/monthly_skew_signals_smoothed.parquet"
    monthly_skew.to_parquet(signal_output_path, index=False)
    
    print("Loading existing adjusted equity closes...")
    prices = pd.read_parquet("data/processed/equity_adj_closes.parquet")
    signals = pd.read_parquet(signal_output_path)
    
    signals['REBAL_DATE'] = pd.to_datetime(signals['REBAL_DATE'])
    prices['DATE'] = pd.to_datetime(prices['DATE'])
    
    print("Running Smoothed Cross-Sectional Backtest...")
    results = run_cross_sectional_backtest_v2(signals, prices)
    
    rets = results['bucket_returns']
    ic = results['ic']
    turnover = results['turnover']

    print("\n--- SMOOTHED MONEYNESS: ANNUALIZED BACKTEST RESULTS ---")
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

    print("\n--- SMOOTHED MONEYNESS: SIGNAL METRICS ---")
    print(f"Mean Rank IC: {ic.mean():.4f}")
    print(f"IC IR (Annualized): {(ic.mean() / ic.std()) * np.sqrt(12):.4f}")
    print(f"Average Q1 Monthly Turnover: {turnover.mean():.2%}")

if __name__ == "__main__":
    main()