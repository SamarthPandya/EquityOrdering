import pandas as pd

def build_monthly_skew_signal_v2_delta(clean_options_v2_df: pd.DataFrame) -> pd.DataFrame:
    df = clean_options_v2_df.copy()
    
    # 1. Pivot IV and Volume
    pivoted_iv = df.pivot_table(index=['DATE', 'SYMBOL'], columns='OPT_TYPE', values='IV').reset_index()
    pivoted_vol = df.pivot_table(index=['DATE', 'SYMBOL'], columns='OPT_TYPE', values='VOLUME').reset_index()
    
    pivoted = pd.merge(pivoted_iv, pivoted_vol, on=['DATE', 'SYMBOL'], suffixes=('_IV', '_VOL'))
    pivoted = pivoted.dropna(subset=['CE_IV', 'PE_IV'])
    
    # 2. Skew Math
    pivoted['DAILY_SKEW'] = (pivoted['PE_IV'] - pivoted['CE_IV']) / pivoted['CE_IV']
    
    # 3. Volume Weighting
    pivoted['TOTAL_VOL'] = pivoted['PE_VOL'] + pivoted['CE_VOL']
    pivoted['VOL_x_SKEW'] = pivoted['DAILY_SKEW'] * pivoted['TOTAL_VOL']
    
    # 4. Roll up to Monthly Signal
    pivoted['MONTH'] = pivoted['DATE'].dt.to_period('M')
    pivoted = pivoted.sort_values(['SYMBOL', 'DATE'])
    last_5_days = pivoted.groupby(['MONTH', 'SYMBOL']).tail(5)
    
    monthly_signal = last_5_days.groupby(['MONTH', 'SYMBOL']).agg(
        REBAL_DATE=('DATE', 'max'),       
        VALID_DAYS=('DAILY_SKEW', 'count'), 
        SUM_VOL_x_SKEW=('VOL_x_SKEW', 'sum'),
        SUM_VOL=('TOTAL_VOL', 'sum')
    ).reset_index()
    
    monthly_signal = monthly_signal[monthly_signal['VALID_DAYS'] >= 2].copy()
    monthly_signal['MONTHLY_SKEW_V2'] = monthly_signal['SUM_VOL_x_SKEW'] / monthly_signal['SUM_VOL']
    
    # --- THE FIX: Align REBAL_DATE globally for the cross-section ---
    # This guarantees the backtester compares all 200 stocks simultaneously
    monthly_signal['REBAL_DATE'] = monthly_signal.groupby('MONTH')['REBAL_DATE'].transform('max')
    
    # 5. EMA Smoothing
    monthly_signal = monthly_signal.sort_values(['SYMBOL', 'REBAL_DATE'])
    monthly_signal['SKEW_EMA'] = monthly_signal.groupby('SYMBOL')['MONTHLY_SKEW_V2'].transform(
        lambda x: x.ewm(span=3, min_periods=1).mean()
    )
    
    return monthly_signal[['REBAL_DATE', 'SYMBOL', 'MONTHLY_SKEW_V2', 'SKEW_EMA', 'VALID_DAYS']]