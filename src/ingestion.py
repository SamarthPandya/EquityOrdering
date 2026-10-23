# one time ingestion to .parquet format for quick access

import pandas as pd
import numpy as np

def parse_single_bhavcopy(file_path: str) -> pd.DataFrame:
    """
    Reads a single NSE F&O Bhavcopy, applies liquidity and moneyness filters,
    and returns a clean DataFrame with the optimal ATM Call and OTM Put per stock.
    """

    df = pd.read_csv(file_path)
    
    col_map = {
        'TIMESTAMP': 'DATE', 'TradDt': 'DATE',
        'INSTRUMENT': 'INSTRUMENT', 'FinInstrmTp': 'INSTRUMENT',
        'SYMBOL': 'SYMBOL', 'TckrSymb': 'SYMBOL',
        'EXPIRY_DT': 'EXPIRY_DT', 'XpryDt': 'EXPIRY_DT',
        'STRIKE_PR': 'STRIKE', 'StrkPric': 'STRIKE',
        'OPTION_TYP': 'OPT_TYPE', 'OptnTp': 'OPT_TYPE',
        'CLOSE': 'CLOSE', 'ClsPric': 'CLOSE',
        'CONTRACTS': 'VOLUME', 'TtlTradgVol': 'VOLUME',
        'OPEN_INT': 'OI', 'OpnIntrst': 'OI'
    }
    df = df.rename(columns=lambda c: col_map.get(c, c))
    
    df['DATE'] = pd.to_datetime(df['DATE'], format='mixed', dayfirst=True)
    df['EXPIRY_DT'] = pd.to_datetime(df['EXPIRY_DT'], format='mixed', dayfirst=True)
    df = df[df['INSTRUMENT'].isin(['FUTSTK', 'OPTSTK', 'STF', 'STO'])].copy()
    df['DTE'] = (df['EXPIRY_DT'] - df['DATE']).dt.days
    df = df[(df['DTE'] >= 10) & (df['DTE'] <= 60)]
    
    if df.empty:
        return pd.DataFrame()
    
    # Futures Baseline (F_t) for black 76
    futures = df[df['INSTRUMENT'].isin(['FUTSTK', 'STF'])][
        ['DATE', 'SYMBOL', 'EXPIRY_DT', 'CLOSE']
    ].rename(columns={'CLOSE': 'FUT_CLOSE'})
    

    futures = futures.drop_duplicates(subset=['SYMBOL', 'EXPIRY_DT'])
    
    options = df[df['INSTRUMENT'].isin(['OPTSTK', 'STO'])].copy()
    options = options[(options['VOLUME'] > 0) & (options['OI'] > 0) & (options['CLOSE'] > 0.50)]
    options = pd.merge(options, futures, on=['DATE', 'SYMBOL', 'EXPIRY_DT'], how='inner')
    
    options['MONEYNESS'] = options['STRIKE'] / options['FUT_CLOSE']
    atm_calls = options[
        (options['OPT_TYPE'] == 'CE') & 
        (options['MONEYNESS'].between(0.95, 1.05))
    ].copy()
    atm_calls['DIST_TO_TARGET'] = (atm_calls['MONEYNESS'] - 1.00).abs()
    otm_puts = options[
        (options['OPT_TYPE'] == 'PE') & 
        (options['MONEYNESS'] >= 0.80) & 
        (options['MONEYNESS'] < 0.95)
    ].copy()
    otm_puts['DIST_TO_TARGET'] = (otm_puts['MONEYNESS'] - 0.95).abs()
    
    # Closest to target moneyness
    best_calls = atm_calls.sort_values('DIST_TO_TARGET').groupby(['DATE', 'SYMBOL']).first().reset_index()
    best_puts = otm_puts.sort_values('DIST_TO_TARGET').groupby(['DATE', 'SYMBOL']).first().reset_index()
    
    # final df
    filtered_daily_chain = pd.concat([best_calls, best_puts], ignore_index=True)
    
    return filtered_daily_chain[
        ['DATE', 'SYMBOL', 'EXPIRY_DT', 'DTE', 'OPT_TYPE', 'STRIKE', 'FUT_CLOSE', 'CLOSE', 'VOLUME', 'OI']
    ]

def process_bhavcopy_batch(file_paths: list) -> pd.DataFrame:
    """
    processing wrapper
    """
    processed_dfs = []
    for path in file_paths:
        try:
            df = parse_single_bhavcopy(path)
            if not df.empty:
                processed_dfs.append(df)
        except Exception as e:
            print(f"Error processing {path}: {e}")
            
    if not processed_dfs:
        return pd.DataFrame()
        
    return pd.concat(processed_dfs, ignore_index=True)