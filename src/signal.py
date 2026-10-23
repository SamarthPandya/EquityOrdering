import pandas as pd
from src.iv_engine import compute_iv

def build_monthly_skew_signal(clean_options_df: pd.DataFrame, risk_free_rate=0.065) -> pd.DataFrame:
    """
    Computes daily IV, calculates daily SKEW, and aggregates into a 
    monthly point-in-time signal based on a 5-day trailing average.
    """
    df = clean_options_df.copy()
    
    # 1. Compute Time to Expiry (in years)
    df['T'] = df['DTE'] / 365.0
    
    # 2. Compute Implied Volatility row-by-row
    df['IV'] = df.apply(
        lambda row: compute_iv(
            market_price=row['CLOSE'],
            F=row['FUT_CLOSE'],
            K=row['STRIKE'],
            T=row['T'],
            r=risk_free_rate,
            opt_type=row['OPT_TYPE']
        ), axis=1
    )
    
    # Drop rows where IV solver failed (usually due to illiquid prices below intrinsic)
    df = df.dropna(subset=['IV'])
    
    # 3. Pivot so Calls and Puts are on the same row per day
    pivoted = df.pivot_table(
        index=['DATE', 'SYMBOL'],
        columns='OPT_TYPE',
        values='IV'
    ).reset_index()
    
    # Ensure both CE and PE exist for the day to calculate Skew
    pivoted = pivoted.dropna(subset=['CE', 'PE'])
    
    # 4. Compute Daily Skew (OTM Put - ATM Call)
    pivoted['DAILY_SKEW'] = pivoted['PE'] - pivoted['CE']
    
    # 5. Roll up to Monthly Signal (Strictly the last 5 trading days)
    pivoted['MONTH'] = pivoted['DATE'].dt.to_period('M')
    
    # Sort chronologically to ensure .tail(5) grabs the end of the month
    pivoted = pivoted.sort_values(['SYMBOL', 'DATE'])
    
    # Isolate the last 5 trading days per symbol per month
    last_5_days = pivoted.groupby(['MONTH', 'SYMBOL']).tail(5)
    
    # Now aggregate
    monthly_signal = last_5_days.groupby(['MONTH', 'SYMBOL']).agg(
        REBAL_DATE=('DATE', 'max'),       
        VALID_DAYS=('DAILY_SKEW', 'count'), 
        MONTHLY_SKEW=('DAILY_SKEW', 'mean') 
    ).reset_index()
    
    # Require at least 2 valid days out of those final 5
    monthly_signal = monthly_signal[monthly_signal['VALID_DAYS'] >= 2]
    
    return monthly_signal[['REBAL_DATE', 'SYMBOL', 'MONTHLY_SKEW', 'VALID_DAYS']]