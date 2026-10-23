import pandas as pd
import yfinance as yf
import numpy as np

def fetch_forward_returns(monthly_skew_df: pd.DataFrame) -> pd.DataFrame:
    """
    Identifies the unique symbols and dates required, fetches adjusted closes,
    and computes the 1-month forward return (from t+1 to t'+1).
    """
    # 1. Get unique NSE symbols and format for yfinance (add .NS)
    unique_symbols = monthly_skew_df['SYMBOL'].unique()
    yf_tickers = [f"{sym}.NS" for sym in unique_symbols]
    
    print(f"Fetching daily adjusted prices for {len(yf_tickers)} stocks...")
    
    # 2. Download batch data (Jan 2021 to Feb 2024 to catch the final forward return)
    # yfinance returns a MultiIndex dataframe when downloading multiple tickers
    price_data = yf.download(
        yf_tickers, 
        start="2021-01-01", 
        end="2024-02-15",   
        auto_adjust=True, # Automatically handles splits/bonuses
        progress=True
    )['Close']
    
    # 3. Clean up the DataFrame
    # Strip the '.NS' to match our Bhavcopy symbols
    price_data.columns = [col.replace('.NS', '') for col in price_data.columns]
    price_data = price_data.reset_index()
    price_data = price_data.melt(id_vars=['Date'], var_name='SYMBOL', value_name='ADJ_CLOSE')
    price_data = price_data.rename(columns={'Date': 'DATE'})
    
    # Drop NaNs (weekends, holidays, or delisted stocks)
    price_data = price_data.dropna(subset=['ADJ_CLOSE'])
    
    # 4. Save to parquet
    output_path = "data/processed/equity_adj_closes.parquet"
    price_data.to_parquet(output_path, index=False)
    print(f"Saved adjusted closes to {output_path}")
    
    return price_data