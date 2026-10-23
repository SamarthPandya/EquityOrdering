import pandas as pd
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq

# --- Math Helpers ---
def black76_price(F, K, T, r, sigma, opt_type):
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    df = np.exp(-r * T)
    if opt_type == 'CE': return df * (F * norm.cdf(d1) - K * norm.cdf(d2))
    else: return df * (K * norm.cdf(-d2) - F * norm.cdf(-d1))

def get_iv_and_delta(row, r=0.065):
    F, K, T, P, opt_type = row['FUT_CLOSE'], row['STRIKE'], row['T'], row['CLOSE'], row['OPT_TYPE']
    intrinsic = np.exp(-r * T) * max(0.0, (F - K) if opt_type == 'CE' else (K - F))
    
    if P <= intrinsic + 1e-4: 
        return pd.Series([np.nan, np.nan])
        
    try:
        iv = brentq(lambda s: black76_price(F, K, T, r, s, opt_type) - P, 0.01, 3.0, xtol=1e-4)
        d1 = (np.log(F / K) + 0.5 * iv**2 * T) / (iv * np.sqrt(T))
        delta = np.exp(-r * T) * norm.cdf(d1) if opt_type == 'CE' else np.exp(-r * T) * (norm.cdf(d1) - 1)
        return pd.Series([iv, delta])
    except:
        return pd.Series([np.nan, np.nan])

# --- Core Ingestion ---
def parse_single_bhavcopy_v2(file_path: str) -> pd.DataFrame:
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
    df['T'] = df['DTE'] / 365.0
    df = df[(df['DTE'] >= 10) & (df['DTE'] <= 60)]
    
    if df.empty: return pd.DataFrame()
    
    futures = df[df['INSTRUMENT'].isin(['FUTSTK', 'STF'])][
        ['DATE', 'SYMBOL', 'EXPIRY_DT', 'CLOSE']
    ].rename(columns={'CLOSE': 'FUT_CLOSE'})
    futures = futures.drop_duplicates(subset=['SYMBOL', 'EXPIRY_DT'])
    
    options = df[df['INSTRUMENT'].isin(['OPTSTK', 'STO'])].copy()
    options = options[(options['VOLUME'] > 0) & (options['OI'] > 0) & (options['CLOSE'] > 0.50)]
    options = pd.merge(options, futures, on=['DATE', 'SYMBOL', 'EXPIRY_DT'], how='inner')
    
    # --- NEW FIX: Lock to the Primary Expiration ---
    # Find the expiry with the highest total volume for the stock on that day
    primary_expiry = options.groupby(['DATE', 'SYMBOL', 'EXPIRY_DT'])['VOLUME'].sum().reset_index()
    primary_expiry = primary_expiry.sort_values(['DATE', 'SYMBOL', 'VOLUME'], ascending=[True, True, False])
    primary_expiry = primary_expiry.groupby(['DATE', 'SYMBOL']).first().reset_index()
    
    # Filter options chain to ONLY keep the most liquid expiration date
    options = pd.merge(options, primary_expiry[['DATE', 'SYMBOL', 'EXPIRY_DT']], on=['DATE', 'SYMBOL', 'EXPIRY_DT'], how='inner')
    # -----------------------------------------------
    
    # 1. Broad Pre-Filter (Saves 80% compute time)
    options['MONEYNESS'] = options['STRIKE'] / options['FUT_CLOSE']
    mask_ce = (options['OPT_TYPE'] == 'CE') & (options['MONEYNESS'].between(0.95, 1.15)) 
    mask_pe = (options['OPT_TYPE'] == 'PE') & (options['MONEYNESS'].between(0.70, 0.98)) 
    options = options[mask_ce | mask_pe].copy()
    
    if options.empty: return pd.DataFrame()
    
    # 2. Calculate Exact IV & Delta
    options[['IV', 'DELTA']] = options.apply(get_iv_and_delta, axis=1)
    options = options.dropna(subset=['IV', 'DELTA'])
    
    # 3. Target Delta Matching
    ce_candidates = options[options['OPT_TYPE'] == 'CE'].copy()
    ce_candidates['DIST_TO_TARGET'] = (ce_candidates['DELTA'] - 0.50).abs()
    
    pe_candidates = options[options['OPT_TYPE'] == 'PE'].copy()
    pe_candidates['DIST_TO_TARGET'] = (pe_candidates['DELTA'] - (-0.10)).abs()
    
    best_calls = ce_candidates.sort_values('DIST_TO_TARGET').groupby(['DATE', 'SYMBOL']).first().reset_index()
    best_puts = pe_candidates.sort_values('DIST_TO_TARGET').groupby(['DATE', 'SYMBOL']).first().reset_index()
    
    filtered_daily_chain = pd.concat([best_calls, best_puts], ignore_index=True)
    
    return filtered_daily_chain[
        ['DATE', 'SYMBOL', 'EXPIRY_DT', 'DTE', 'OPT_TYPE', 'STRIKE', 'FUT_CLOSE', 'CLOSE', 'VOLUME', 'OI', 'IV', 'DELTA']
    ]

def process_bhavcopy_batch_v2(file_paths: list) -> pd.DataFrame:
    processed_dfs = []
    for path in file_paths:
        try:
            df = parse_single_bhavcopy_v2(path)
            if not df.empty:
                processed_dfs.append(df)
        except Exception as e:
            print(f"Error processing {path}: {e}")
            
    if not processed_dfs: return pd.DataFrame()
    return pd.concat(processed_dfs, ignore_index=True)