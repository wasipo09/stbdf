from constants import TOKEN_FACTOR_10, ZSCORE_THRESH, ZSCORE_CROSSING
from func_utils import format_number
from func_public import get_candles_recent
from func_cointegration import calculate_zscore
from func_private import is_open_positions
from func_bot_agent import BotAgent
from func_balance import free_collateral, LEVERAGE, USD_PER_TRADE, USD_MIN_COLLATERAL
from func_messaging import send_message_telegram
import pandas as pd
import json


# Round trade size
# def round_half(n):
#     if (str(n).find(".") > 0):
#         decimalsource = len(str(n).split(".")[1])
#         base = 10**decimalsource
#         number = n*base
#         rounded = 5 * round(number/5)
#         result = rounded / base
#         if (result == int(result)):
#             return int(result)
#         else:
#             return result
#     elif n == 1:
#         return n
#     else:
#         return 5 * round(n/5)


# Open positions
def open_positions(client):
    try:
        while True:
            '''
            Manage finding triggers for trade entry
            Store trades for managing later on on exit function
            '''

            print('Finding trading opportunities...')

            # Load cointegrated pairs
            df = pd.read_csv('cointegrated_pairs.csv')

            # Get markets from referencing of min order size, tick size etc
            markets = client.public.get_markets().data

            # Initialize container for BotAgent results
            bot_agents = []

            # Opening JSON file
            try:
                open_positions_file = open('bot_agents.json')
                open_positions_dict = json.load(open_positions_file)
                for p in open_positions_dict:
                    bot_agents.append(p)
            except:
                bot_agents = []

            # Find ZScore triggers
            for index, row in df.iterrows():

                # Extract variables
                base_market = row['base_market']
                quote_market = row['quote_market']
                hedge_ratio = row['hedge_ratio']
                zero_crossings = row['zero_crossings']
                half_life = row['half_life']

                # Get prices
                series_1 = get_candles_recent(client, base_market)
                series_2 = get_candles_recent(client, quote_market)

                # If the pair has crossen 0 x times
                if zero_crossings >= ZSCORE_CROSSING:

                    # Get ZScore
                    if len(series_1) > 0 and len(series_1) == len(series_2):
                        spread = series_1 - (hedge_ratio * series_2)
                        z_score = calculate_zscore(spread).values.tolist()[-1]

                        # Establish if potential trade
                        if abs(z_score) >= ZSCORE_THRESH:

                            # Ensure like-for-like not already open (diversify trading)
                            is_base_open = is_open_positions(
                                client, base_market)
                            is_quote_open = is_open_positions(
                                client, quote_market)

                            # Place trade
                            if not is_base_open and not is_quote_open:

                                # Determine side
                                base_side = 'BUY' if z_score < 0 else 'SELL'
                                quote_side = 'BUY' if z_score > 0 else 'SELL'

                                # Get acceptable price in string format with correct number of decimals
                                base_price = series_1[-1]
                                quote_price = series_2[-1]
                                accept_base_price = float(
                                    base_price) * 1.01 if z_score < 0 else float(base_price) * 0.99
                                accept_quote_price = float(
                                    quote_price) * 1.01 if z_score > 0 else float(quote_price) * 0.99
                                failsafe_base_price = float(
                                    base_price) * 0.05 if z_score < 0 else float(base_price) * 1.7
                                base_tick_size = markets['markets'][base_market]['tickSize']
                                quote_tick_size = markets['markets'][quote_market]['tickSize']

                                # Format prices
                                accept_base_price = format_number(
                                    accept_base_price, base_tick_size)
                                accept_quote_price = format_number(
                                    accept_quote_price, quote_tick_size)
                                accept_failsafe_base_price = format_number(
                                    failsafe_base_price, base_tick_size)

                                # Get size
                                base_quantity = 1 / base_price * USD_PER_TRADE
                                quote_quantity = 1 / quote_price * USD_PER_TRADE
                                base_step_size = markets['markets'][base_market]['stepSize']
                                quote_step_size = markets['markets'][quote_market]['stepSize']

                                # Token size must be a factor of 10, coins limitation
                                for x in TOKEN_FACTOR_10:
                                    if base_market == x:
                                        base_quantity = float(
                                            int(base_quantity / 10) * 10)
                                    elif quote_market == x:
                                        quote_quantity = float(
                                            int(quote_quantity / 10) * 10)

                                # Format sizes - stackoverlflow workaround but now there the function above that does the rounding
                                # base_size = round_half(
                                #     float(format_number(base_quantity, base_step_size)))
                                # quote_size = round_half(
                                #     float(format_number(quote_quantity, quote_step_size)))
                                # base_size = str(base_size)
                                # quote_size = str(quote_size)

                                base_size = format_number(
                                    base_quantity, base_step_size)
                                quote_size = format_number(
                                    quote_quantity, quote_step_size)

                                # print(f'Base Size: {base_size}',
                                #       f'Quote Size: {quote_size}')

                                # Ensure size
                                base_min_order_size = markets['markets'][base_market]['minOrderSize']
                                quote_min_order_size = markets['markets'][quote_market]['minOrderSize']
                                check_base = float(base_quantity) > float(
                                    base_min_order_size)
                                check_quote = float(quote_quantity) > float(
                                    quote_min_order_size)

                                # If checks pass, place trades
                                if check_base and check_quote:

                                    # Check account balance
                                    account = client.private.get_account()
                                    free_collateral = float(
                                        account.data['account']['freeCollateral'])
                                    print(
                                        f'Balance: {free_collateral} and minimum at {USD_MIN_COLLATERAL}')

                                    # Guard: Ensure collateral
                                    if free_collateral < USD_MIN_COLLATERAL:
                                        send_message_telegram(
                                            f'Free collateral: {free_collateral} is < than: {USD_MIN_COLLATERAL} minimum collateral')
                                        break

                                    # Create Bot Agent
                                    bot_agent = BotAgent(
                                        client,
                                        market_1=base_market,
                                        market_2=quote_market,
                                        base_side=base_side,
                                        base_size=base_size,
                                        base_price=accept_base_price,
                                        quote_side=quote_side,
                                        quote_size=quote_size,
                                        quote_price=accept_quote_price,
                                        accept_failsafe_base_price=accept_failsafe_base_price,
                                        z_score=z_score,
                                        half_life=half_life,
                                        hedge_ratio=hedge_ratio
                                    )

                                    # Open Trades
                                    bot_open_dict = bot_agent.open_trades()

                                    # Guard: Handle failure
                                    if bot_open_dict == 'failed':
                                        continue

                                    # Handle success in opening trades
                                    if bot_open_dict['pair_status'] == 'LIVE':

                                        # Append to list of bot agents
                                        bot_agents.append(bot_open_dict)
                                        del (bot_open_dict)

                                        # Confirm live status in print
                                        print('Trade status: Live')
                                        print('---')

                                        # side_1 = 'Long' if base_side == 'BUY' else 'Short'
                                        # side_2 = 'Long' if quote_side == 'BUY' else 'Short'
                                        # send_message_telegram(f'Trading: {base_market}\nDirection: {side_1}\nCoin size: {base_size}\nTrade size: ${USD_PER_TRADE}\n{base_market} Price: ${base_price}\n\nTrading: {quote_market}\nDirection: {side_2}\nCoin size: {quote_size}\nTrade size: ${USD_PER_TRADE}\n{quote_market} Price: ${quote_price}\n\nLeverage used: {LEVERAGE}x\nFree collateral: ${round(free_collateral, 2)}')

            # Save agents
            print('Success: Manage open trades checked')
            if len(bot_agents) > 0:
                with open('bot_agents.json', 'w') as f:
                    json.dump(bot_agents, f)
    except Exception as e:
        print(f'Thread closed due to timeout, Error: {e}')
