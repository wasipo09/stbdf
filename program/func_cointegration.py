import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
from constants import MAX_HALF_LIFE, WINDOW
from func_messaging import send_message_telegram
from datetime import datetime, timedelta
# Calculate Half Life
# https://www.pythonforfinance.net/2016/05/09/python-backtesting-mean-reversion-part-2/


# Calculate Half Life
def calculate_half_life(spread):
    df_spread = pd.DataFrame(spread, columns=['spread'])
    spread_lag = df_spread.spread.shift(1)
    spread_lag.iloc[0] = spread_lag.iloc[1]
    spread_ret = df_spread.spread - spread_lag
    spread_ret.iloc[0] = spread_ret.iloc[1]
    spread_lag2 = sm.add_constant(spread_lag)
    model = sm.OLS(spread_ret, spread_lag2)
    res = model.fit()
    halflife = round(-np.log(2) / res.params[1], 0)
    return halflife


# Calculate Z-Score
def calculate_zscore(spread):
    spread_series = pd.Series(spread)
    mean = spread_series.rolling(center=False, window=WINDOW).mean()
    std = spread_series.rolling(center=False, window=WINDOW).std()
    x = spread_series.rolling(center=False, window=1).mean()
    zscore = (x - mean) / std
    return zscore


# Calculate Cointegration
def calculate_cointegration(series_1, series_2):
    series_1 = np.array(series_1).astype(np.float)
    series_2 = np.array(series_2).astype(np.float)
    coint_flag = 0
    coint_res = coint(series_1, series_2)
    p_value = coint_res[1]
    coint_t = coint_res[0]
    critical_value = coint_res[2][1]
    model = sm.OLS(series_1, series_2).fit()
    hedge_ratio = model.params[0]
    spread = series_1 - (hedge_ratio * series_2)
    zero_crossings = len(np.where(np.diff(np.sign(spread)))[0])
    zscore = round(calculate_zscore(spread).values.tolist()[-1],2)
    half_life = calculate_half_life(spread)
    t_check = coint_t < critical_value
    coint_flag = 1 if p_value < 0.05 and t_check else 0
    base_side = 'BUY' if zscore < 0 else 'SELL'
    quote_side = 'BUY' if zscore > 0 else 'SELL'
    return base_side, quote_side, zscore, coint_flag, round(p_value, 2), round(coint_t, 2), round(critical_value, 2), round(hedge_ratio, 2), half_life, zero_crossings


# Store Cointegration Results
def store_cointegration_results(df_market_prices):

    # Initialize
    markets = df_market_prices.columns.to_list()
    criteria_met_pairs = []

    # Find cointegrated pairs
    # Start with our base pair
    for index, base_market in enumerate(markets[:-1]):
        series_1 = df_market_prices[base_market].values.astype(float).tolist()

        # Get Quote Pair
        for quote_market in markets[index + 1:]:
            series_2 = df_market_prices[quote_market].values.astype(
                float).tolist()

            # Check cointegration
            base_side, quote_side, zscore, coint_flag, p_value, t_value, critical_value, hedge_ratio, half_life, zero_crossings = calculate_cointegration(
                series_1, series_2)

            # Log pair
            if coint_flag == 1 and half_life <= MAX_HALF_LIFE and half_life > 0:
                criteria_met_pairs.append({
                    'base_market': base_market,
                    'quote_market': quote_market,
                    'p_value': p_value,
                    't_value': t_value,
                    'c_value': critical_value,
                    'hedge_ratio': hedge_ratio,
                    'half_life': half_life,
                    'zero_crossings': zero_crossings,
                    'zscore':zscore,
                    'base_side':base_side,
                    'quote_side':quote_side
                })

    # Create and save DataFrame
    df_criteria_met = pd.DataFrame(criteria_met_pairs)
    df_criteria_met.to_csv('cointegrated_pairs.csv')

    utc_time = datetime.utcnow()
    

    df_criteria_met = df_criteria_met[((df_criteria_met['zscore'] < -1) | (df_criteria_met['zscore'] > 1)) & (df_criteria_met['p_value'] < 0.02)]
    df_criteria_met.sort_values(by='half_life', inplace=True)

    if not df_criteria_met.empty:
        # Assuming df_criteria_met is your filtered DataFrame
        for index, row in df_criteria_met.iterrows():
            bkk_time = utc_time + timedelta(hours=7)
            close_time = bkk_time + timedelta(hours=int(row['half_life']))

            send_message_telegram(f"{row['base_side']} {row['base_market']} | {row['quote_side']} {row['quote_market']} \nZ-Score: {row['zscore']} \nHalf-Life: {row['half_life']} \nZero-Crossings: {row['zero_crossings']} \nExpiry: {close_time.strftime('%Y-%m-%d %H:%M¥')}")
    else:
       send_message_telegram('No pair detected.')

    del df_criteria_met
    # Return result
    print('Cointegrated pairs successfully saved')
    return 'saved'
