# Note : Investigation of Skew Based Signal
This note documents the hypothesis, testing, corresponding justications and conclusion
of investigation into skew based signal for equity ordering.


## Base Variables & Parameters
For any given trading day $t$ and stock $i$:
* **$F_{t}$**: End-of-day price of the underlying Futures contract.
* **$K$**: Strike price of the option contract.
* **$T$**: Time to expiration in years ($DTE / 256$).
* **Maturity Constraint**: Only contracts with a Days to Expiration (DTE) strictly between 10 and 60 days are considered ($10 \le DTE \le 60$).

## Moneyness
Moneyness ($M$) is the ratio of the option's strike price to the underlying futures baseline:

$$ M = \frac{K}{F_{t}} $$

## Universe Filtering & Contract Selection
For each stock on day $t$, we isolate the exact contracts used for the calculation by minimizing the distance to a target moneyness. Begin by filtering options that pass baseline liquidity filters: 
* $Volume > 0$
* $Open\ Interest > 0$
* $Close\ Price > 0.50$

**ATM Call Selection**
1. **Define Universe**: Filter all Call options ($CE$) where $0.95 \le M \le 1.05$.
2. **Calculate Distance**: Calculate the absolute distance to At-The-Money: 
   $$ Dist_{CE} = |M - 1.00| $$
3. **Select**: Select the single Call contract that minimizes $Dist_{CE}$.

**OTM Put Selection**
1. **Define Universe**: Filter all Put options ($PE$) where $0.80 \le M < 0.95$.
2. **Calculate Distance**: Calculate the absolute distance to 5% Out-of-The-Money: 
   $$ Dist_{PE} = |M - 0.95| $$
3. **Select**: Select the single Put contract that minimizes $Dist_{PE}$.

## Skew Calculation

### Daily Skew
Using a Black-76 implied volatility solver ($IV$), compute the volatility for the selected contracts and calculate the spread. Bhavcopies provide the future price which allows for convenient use of Black-76 model.

$$ Skew_{t} = IV(PE_{selected}) - IV(CE_{selected}) $$

### Monthly Aggregated Signal

To generate the final monthly signal for month $M$, apply a trailing average over the final trading days of that month:
1. Isolate the **last 5 trading days** of month $M$ for the stock.
2. Count the number of valid days within this 5-day window where $Skew_{t}$ was successfully computed.
3. **Validity Condition**: If the count of valid days $\ge 2$, proceed. Otherwise, drop the stock for that month.
4. **Final Signal**: 
   $$ Signal_{M} = \frac{1}{N} \sum_{i=0}^{N-1} Skew_{t_{end}-i} $$
*(Where $t_{end}$ is the final trading day of the month, and $N$ is the number of valid days in the 5-day window).*

## Justifications

**Futures Baseline ($F_t$) & Black-76:** Using the underlying futures price natively includes the cost-of-carry (interest rates and discrete dividend expectations). This eliminates the need to construct dynamic yield curves or estimate dividend drop schedules.

**Maturity Window ($10 \le DTE \le 60$):** Excludes short-dated contracts ($DTE < 10$) to avoid expiration week noise and gamma-driven price noise. It also removes far-month contracts ($DTE > 60$) where lower liquidity and wider spreads corrupt the IV calculation.

**Baseline Liquidity Filters:** Requiring volume, open interest, and a minimum premium floor ensures the signal is derived from active market participation.

**Moneyness Targeting (ATM Call vs. 5% OTM Put):** Subtracting ATM Call IV from OTM Put IV isolates the pure "fear premium" (downside tail risk) by stripping out the base level of market variance. The 0.95 target specifically captures institutional hedging demand while avoiding the extreme bid-ask noise of deep OTM strikes.

**Distance Minimization Selection:** Selecting the closest physically traded strike rather than interpolating a synthetic constant-moneyness IV guarantees that the signal relies on real, executable order-book pricing rather than theoretical curve approximations.

**5-Day Trailing Aggregation:** Averaging the final five trading days of the month smooths out  microstructure noise, such as  order imbalances or macro shocks. It captures a more persistent, structural view of positions heading into the next month.

**Validity Condition ($\ge 2$ days):** Enforcing a minimum day count ensures robustness, preventing the aggregated monthly signal from being disproportionately skewed by a single day of anomalous data.

## Backtesting

### Data & Universe Scope

**Source:** Daily NSE Bhavcopies. The dataset utilizes end-of-day pricing, volume, and open interest strictly for equity derivatives (Instruments: `FUTSTK`, `OPTSTK`, `STF`, `STO`), filtering out index derivatives.

**Universe:** NSE F&O (Futures and Options) designated equities. The cross-sectional universe is dynamically defined as mentioned above.

**Time Horizon:** The empirical backtest spans a 35-month continuous period. Data is processed at a daily frequency to construct the signal, which is then aggregated and applied to a monthly portfolio rebalancing frequency.

### Method
To evaluate the predictive power of the monthly skew signal, we apply cross-sectional portfolio sorting at the end of each month.

**Cross-Sectional Ranking:** On the final trading day of month $M$, all eligible equities are ranked cross-sectionally based on their aggregated $Signal_{M}$ values.

**Portfolio Construction:** The ranked universe is segmented into equal-weighted quintile buckets (e.g., Q1 representing the lowest skew, Q5 representing the highest).

**Performance Evaluation:** 
  * **Forward Returns:** Calculate the subsequent 1-month forward return for each bucket to test for monotonic outperformance (e.g., a long-short spread between Q5 and Q1).
  * **Information Coefficient (IC):** Compute the Spearman rank correlation between the cross-sectional signal scores and the forward 1-month returns/
  * **Turnover:** Track the month-to-month percentage of portfolio constituent changes.

### Results

Total Months Tested: 35

**Annualized Returns by Quintile:**
* **Q1 (Lowest Skew):** 16.54%
* **Q2:** 16.54%
* **Q3:** 15.34%
* **Q4:** 11.70%
* **Q5 (Highest Skew):** 13.78%
* **Universe (Equal-Weight):** 14.78%

**Strategy Spreads:**
* **Long-Only Active (Q1 - EW):** 1.55%
* **Long/Short Spread (Q1 - Q5):** 2.45%
* **Mean Rank IC:** 0.0099
* **IC IR (Annualized):** 0.2986
* **Average Q1 Monthly Turnover:** 72.12%

## 8. Empirical Limitations & Market Microstructure

**Options Liquidity & Spread Noise**
Outside the top ~50 highly liquid Nifty constituents, bid-ask spreads on 5% OTM puts can widen to 5–10% of the option premium. While our baseline filters (Volume > 0, Close > 0.50) discard completely dead strikes, the Bhavcopy closing price on illiquid names often reflects a stale Last Traded Price (LTP) rather than a true bid-ask midpoint.

**F&O Universe Drift & Ban Periods**
Stocks that hit 95% of their Market Wide Position Limit (MWPL) enter F&O ban periods, during which fresh positions are prohibited. This causes extreme localized liquidity vacuums and premium distortions that our model does not explicitly filter out, potentially biasing bucket assignments during those specific windows.

**Data & Model Hindsight**
Zero look-ahead bias is introduced via the pricing model. IV is solved from scratch locally using strictly point-in-time end-of-day Bhavcopy data. By utilizing the concurrent daily futures close ($F_t$) as the Black-76 underlying baseline, the cost-of-carry is extracted precisely as it was priced on day $t$. No ex-post dividend realizations, smoothed vendor surfaces, or forward-looking yield curves leak into the 35-month historical backtest.

**India vs. US Market Structure**
Unlike US single-stock options, NSE equity derivatives are subject to physical settlement and strict margin requirements that suppress naked retail selling. Consequently, single-stock options on the NSE are heavily dominated by institutional covered writing and proprietary hedging, with volume aggressively concentrated at ATM strikes. The liquidity drop-off at the 0.95 OTM boundary is far steeper in India than in the US. Therefore, the extracted skew premium is less a measure of retail panic and more a reflection of institutional inventory capacity and structural hedging costs.

# Running the Analysis and Inspecting Results

All upstream data has already been processed and consolidated into `.parquet` files via the OTL scripts. What remains is to run the main analysis pipeline.

### 1. Execute the Pipeline
To run the final analysis, simply execute the main script from your terminal: python main.py

### 2. Results

* All csv files can be inspected at data/csv_data
* Any newly generated parquet files can be converted to csv for inspection using the script at **data/processed/convert_to_csv.py**



