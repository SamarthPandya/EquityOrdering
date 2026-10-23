import pandas as pd

def build_smoothed_moneyness_signal(clean_df: pd.DataFrame) -> pd.DataFrame:
    df = clean_df.copy()
    
    # Dynamically detect if we are using IV (V2) or raw Option Price (V1)
    val_col = 'IV' if 'IV' in df.columns else 'CLOSE'
    
    # 1. Pivot Values and Volume
    pivoted_val = df.pivot_table(index=['DATE', 'SYMBOL'], columns='OPT_TYPE', values=val_col).reset_index()
    pivoted_vol = df.pivot_table(index=['DATE', 'SYMBOL'], columns='OPT_TYPE', values='VOLUME').reset_index()
    
    pivoted = pd.merge(pivoted_val, pivoted_vol, on=['DATE', 'SYMBOL'], suffixes=('_VAL', '_VOL'))
    pivoted = pivoted.dropna(subset=['CE_VAL', 'PE_VAL'])
    
    # 2. Raw Skew Math (Simple Moneyness Price Skew)
    pivoted['DAILY_SKEW'] = (pivoted['PE_VAL'] - pivoted['CE_VAL']) / pivoted['CE_VAL']
    
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
    monthly_signal['MONTHLY_SKEW'] = monthly_signal['SUM_VOL_x_SKEW'] / monthly_signal['SUM_VOL']
    
    # --- FIX 1: GLOBAL DATE ALIGNMENT ---
    monthly_signal['REBAL_DATE'] = monthly_signal.groupby('MONTH')['REBAL_DATE'].transform('max')
    
    # --- FIX 2: EMA TURNOVER SMOOTHING ---
    monthly_signal = monthly_signal.sort_values(['SYMBOL', 'REBAL_DATE'])
    monthly_signal['SKEW_EMA'] = monthly_signal.groupby('SYMBOL')['MONTHLY_SKEW'].transform(
        lambda x: x.ewm(span=3, min_periods=1).mean()
    )
    
    return monthly_signal[['REBAL_DATE', 'SYMBOL', 'MONTHLY_SKEW', 'SKEW_EMA', 'VALID_DAYS']]