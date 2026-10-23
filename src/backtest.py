import pandas as pd
import numpy as np
from scipy.stats import spearmanr

def run_cross_sectional_backtest(signals_df: pd.DataFrame, prices_df: pd.DataFrame) -> dict:
    """
    Merges signals with forward returns, ranks into quintiles, and computes IC.
    """
    # Align Dates (1-Day Execution Lag)
    # Get all unique trading days from the price data
    trading_days = sorted(prices_df['DATE'].unique())
    
    def get_next_trading_day(d):
        future_days = [td for td in trading_days if td > d]
        return future_days[0] if future_days else pd.NaT
        
    rebal_dates = sorted(signals_df['REBAL_DATE'].unique())
    date_mapping = {d: get_next_trading_day(d) for d in rebal_dates}
    

    returns_list = []
    for i in range(len(rebal_dates) - 1):
        current_rebal = rebal_dates[i]
        next_rebal = rebal_dates[i+1]
        
        entry_date = date_mapping[current_rebal]
        exit_date = date_mapping[next_rebal]
        
        if pd.isna(entry_date) or pd.isna(exit_date):
            continue
            

        p_entry = prices_df[prices_df['DATE'] == entry_date][['SYMBOL', 'ADJ_CLOSE']].rename(columns={'ADJ_CLOSE': 'P_IN'})
        p_exit = prices_df[prices_df['DATE'] == exit_date][['SYMBOL', 'ADJ_CLOSE']].rename(columns={'ADJ_CLOSE': 'P_OUT'})
        
        # Merge to get return
        rets = pd.merge(p_entry, p_exit, on='SYMBOL')
        rets['FWD_RETURN'] = (rets['P_OUT'] / rets['P_IN']) - 1
        rets['REBAL_DATE'] = current_rebal
        
        returns_list.append(rets[['REBAL_DATE', 'SYMBOL', 'FWD_RETURN']])
        
    fwd_returns_df = pd.concat(returns_list, ignore_index=True)
    
    # Merge Signal with Returns
    merged = pd.merge(signals_df, fwd_returns_df, on=['REBAL_DATE', 'SYMBOL'], how='inner')
    

    # Safety Check: Drop rebalance dates that have fewer than 20 stocks
    stock_counts = merged.groupby('REBAL_DATE').size()
    valid_rebal_dates = stock_counts[stock_counts >= 20].index
    merged = merged[merged['REBAL_DATE'].isin(valid_rebal_dates)].copy()
    
    if merged.empty:
        raise ValueError("No valid rebalance dates left after filtering for minimum stock count. Check your data ingestion.")

   
    merged['QUINTILE'] = merged.groupby('REBAL_DATE')['MONTHLY_SKEW'].transform(
        lambda x: pd.qcut(x.rank(method='first'), q=5, labels=False) + 1
    )
    

    # Bucket Returns
    bucket_rets = merged.groupby(['REBAL_DATE', 'QUINTILE'])['FWD_RETURN'].mean().unstack()
    bucket_rets['EW_UNIVERSE'] = merged.groupby('REBAL_DATE')['FWD_RETURN'].mean()
    bucket_rets['Q1_MINUS_EW'] = bucket_rets[1] - bucket_rets['EW_UNIVERSE']
    bucket_rets['Q1_MINUS_Q5'] = bucket_rets[1] - bucket_rets[5]
    
    # Rank IC
    ic_series = merged.groupby('REBAL_DATE').apply(
        lambda g: spearmanr(-g['MONTHLY_SKEW'], g['FWD_RETURN'])[0]
    )
    
    # Turnover for Q1
    q1_holdings = merged[merged['QUINTILE'] == 1].groupby('REBAL_DATE')['SYMBOL'].apply(set)
    dates = sorted(q1_holdings.index)
    turnover = {}
    for i in range(1, len(dates)):
        prev_set, curr_set = q1_holdings[dates[i-1]], q1_holdings[dates[i]]
        overlap = len(prev_set.intersection(curr_set)) / max(len(curr_set), 1)
        turnover[dates[i]] = 1.0 - overlap
        
    turnover_series = pd.Series(turnover, name='Q1_TURNOVER')
    
    return {
        'bucket_returns': bucket_rets,
        'ic': ic_series,
        'turnover': turnover_series
    }