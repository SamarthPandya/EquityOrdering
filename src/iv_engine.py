import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

def black76_price(F, K, T, r, sigma, opt_type='CE'):
    """
    Computes the European option price using the Black-76 model.
    """
    if T <= 0 or sigma <= 0:
        return 0.0
    
    d1 = (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    df = np.exp(-r * T)
    
    if opt_type == 'CE':
        return df * (F * norm.cdf(d1) - K * norm.cdf(d2))
    else:
        return df * (K * norm.cdf(-d2) - F * norm.cdf(-d1))

def compute_iv(market_price, F, K, T, r=0.065, opt_type='CE'):
    """
    Extracts Implied Volatility by finding the root of the Black-76 formula.
    Returns NaN if the option violates arbitrage bounds or is untradable.
    """
    # Check lower arbitrage bound (Intrinsic Value)
    intrinsic = np.exp(-r * T) * max(0.0, (F - K) if opt_type == 'CE' else (K - F))
    
    if market_price <= intrinsic + 1e-4:
        return np.nan
        
    try:
        # Search for IV between 3% and 250%
        iv = brentq(
            lambda s: black76_price(F, K, T, r, s, opt_type) - market_price,
            0.03, 2.50, xtol=1e-5, maxiter=100
        )
        return iv
    except ValueError:
        # Market price is completely detached from theoretical bounds (often true for deep OTM illiquid strikes)
        return np.nan