from constants import CLOSE_AT_ZSCORE_CROSS
from func_utils import format_number
from func_public import get_candles_recent
from func_cointegration import calculate_zscore
from func_private import place_market_order
from func_balance import balance
from func_messaging import send_message_telegram
from func_balance import LEVERAGE, STOP_LOSS_PERCENTAGE
import json
import time


# Manage trade exits
def manage_trade_exits(client):
    try:
        while True:
            '''
            Manage exiting open positions
            Based upon criteria set in constants
            '''

            print('Managing exits...')

            # Initialize saving output
            save_output = []

            # Opening JSON file
            try:
                open_positions_file = open('bot_agents.json')
                open_positions_dict = json.load(open_positions_file)
            except:
                return 'complete'

            # Guard: Exit if no open positions in file
            if len(open_positions_dict) < 1:
                return 'complete'

            # Get all open positions per trading platform
            exchange_pos = client.private.get_positions(status='OPEN')
            all_exc_pos = exchange_pos.data['positions']
            markets_live = []
            for p in all_exc_pos:
                markets_live.append(p['market'])

            live_orders = []
            for x in all_exc_pos:
                live_orders.append(
                    {'market': x['market'], 'side': x['side'], 'entryPrice': float(x['entryPrice'])})

            oracle_prices = []
            for x in live_orders:
                oracle = client.public.get_markets()
                y = oracle.data['markets'][x['market']]
                oracle_prices.append(
                    {'market': y['market'], 'indexPrice': float(y['indexPrice'])})

            # Protect API
            time.sleep(0.5)

            # Check all saved positions match order record
            # Exit trade according to any exit trade rules
            for position in open_positions_dict:

                # Initialize is_close trigger
                is_close = False

                # Extract position matching information from file - market 1
                position_market_m1 = position['market_1']
                position_size_m1 = position['order_m1_size']
                position_side_m1 = position['order_m1_side']

                # Extract position matching information from file - market 2
                position_market_m2 = position['market_2']
                position_size_m2 = position['order_m2_size']
                position_side_m2 = position['order_m2_side']

                # Protect API
                time.sleep(0.5)

                # Get order info m1 per exchange
                order_m1 = client.private.get_order_by_id(
                    position['order_id_m1'])
                order_market_m1 = order_m1.data['order']['market']
                order_size_m1 = order_m1.data['order']['size']
                order_side_m1 = order_m1.data['order']['side']

                # Protect API
                time.sleep(0.5)

                # Get order info m2 per exchange
                order_m2 = client.private.get_order_by_id(
                    position['order_id_m2'])
                order_market_m2 = order_m2.data['order']['market']
                order_size_m2 = order_m2.data['order']['size']
                order_side_m2 = order_m2.data['order']['side']

                # Perform matching checks
                check_m1 = position_market_m1 == order_market_m1 and float(
                    position_size_m1) == float(order_size_m1) and position_side_m1 == order_side_m1
                check_m2 = position_market_m2 == order_market_m2 and float(
                    position_size_m2) == float(order_size_m2) and position_side_m2 == order_side_m2
                check_live = position_market_m1 in markets_live and position_market_m2 in markets_live

                # Guard: If not all match exit with error
                if not check_m1 or not check_m2 or not check_live:
                    print(
                        f'Warning: Not all open positions match exchange records for {position_market_m1} and {position_market_m2}')
                    continue

                # Get prices
                series_1 = get_candles_recent(client, position_market_m1)
                time.sleep(0.2)
                series_2 = get_candles_recent(client, position_market_m2)
                time.sleep(0.2)

                # Get markets for reference of tick size
                markets = client.public.get_markets().data

                # Protect API
                time.sleep(0.2)

                # Trigger close based on Z-Score
                if CLOSE_AT_ZSCORE_CROSS:

                    # Initialize z_scores
                    hedge_ratio = position['hedge_ratio']
                    z_score_traded = position['z_score']
                    if len(series_1) > 0 and len(series_1) == len(series_2):
                        spread = series_1 - (hedge_ratio * series_2)
                        z_score_current = calculate_zscore(
                            spread).values.tolist()[-1]

                    # Determine trigger
                    z_score_level_check = abs(
                        z_score_current) >= abs(z_score_traded)
                    z_score_cross_check = (z_score_current < 0 and z_score_traded > 0) or (
                        z_score_current > 0 and z_score_traded < 0)

                    # Close trade
                    if z_score_level_check and z_score_cross_check:

                        # Initiate close trigger
                        is_close = True

                ###
                # Add any other close logic you want here
                # Trigger is_close
                ###

                # Stop Loss
                for order in live_orders:
                    order_side = order['side']
                    order_entry_price = order['entryPrice']

                    for order_current_price in oracle_prices:
                        if order_current_price['market'] == order['market']:
                            # If Order Long and current price <= entry price * STOP_LOSS_PERCENTAGE / 100 -> 10% this case since leverage is 10x, close the order, same for short
                            if order_side == 'LONG' and order_current_price['indexPrice'] <= order_entry_price - (order_entry_price * STOP_LOSS_PERCENTAGE / 100):
                                is_close = True
                                break
                            elif order_side == 'SHORT' and order_current_price['indexPrice'] >= order_entry_price + (order_entry_price * STOP_LOSS_PERCENTAGE / 100):
                                is_close = True
                                break

                    if is_close == True:
                        break

                # Close positions if triggered
                if is_close:

                    # Determine side - m1
                    side_m1 = 'SELL'
                    if position_side_m1 == 'SELL':
                        side_m1 = 'BUY'

                    # Determine side - m2
                    side_m2 = 'SELL'
                    if position_side_m2 == 'SELL':
                        side_m2 = 'BUY'

                    # Get and format Price
                    price_m1 = float(series_1[-1])
                    price_m2 = float(series_2[-1])
                    accept_price_m1 = price_m1 * 1.05 if side_m1 == 'BUY' else price_m1 * 0.95
                    accept_price_m2 = price_m2 * 1.05 if side_m2 == 'BUY' else price_m2 * 0.95
                    tick_size_m1 = markets['markets'][position_market_m1]['tickSize']
                    tick_size_m2 = markets['markets'][position_market_m2]['tickSize']
                    accept_price_m1 = format_number(
                        accept_price_m1, tick_size_m1)
                    accept_price_m2 = format_number(
                        accept_price_m2, tick_size_m2)

                    # Close positions
                    try:

                        # Close position for market 1
                        print('>>> Closing market 1 <<<')
                        print(f'Closing position for {position_market_m1}')
                        pnl_m1 = client.private.get_positions(
                            market=position_market_m1)
                        unrealized_pnl_m1 = 0
                        for x in pnl_m1.data['positions']:
                            if x['status'] == 'OPEN':
                                unrealized_pnl_m1 = x['unrealizedPnl']

                        close_order_m1 = place_market_order(
                            client,
                            market=position_market_m1,
                            side=side_m1,
                            size=position_size_m1,
                            price=accept_price_m1,
                            reduce_only=True,
                        )

                        print(close_order_m1['order']['id'])
                        print('>>> Closing <<<')
                        # send_message_telegram(
                        #     f'Trade closed: {position_market_m1}, Side: {side_m1}, Size: {position_size_m1}, Price: {accept_price_m1}, PnL: ${unrealized_pnl_m1}')

                        # Protect API
                        time.sleep(1)

                        # Close position for market 2
                        print('>>> Closing market 2 <<<')
                        print(f'Closing position for {position_market_m2}')
                        pnl_m2 = client.private.get_positions(
                            market=position_market_m2)
                        unrealized_pnl_m2 = 0
                        for x in pnl_m2.data['positions']:
                            if x['status'] == 'OPEN':
                                unrealized_pnl_m2 = x['unrealizedPnl']

                        close_order_m2 = place_market_order(
                            client,
                            market=position_market_m2,
                            side=side_m2,
                            size=position_size_m2,
                            price=accept_price_m2,
                            reduce_only=True,
                        )

                        print(close_order_m2['order']['id'])
                        print('>>> Closing <<<')

                        side_1 = 'Long' if side_m1 == 'BUY' else 'Short'
                        side_2 = 'Long' if side_m2 == 'BUY' else 'Short'
                        send_message_telegram(f'Trade closed: {position_market_m1}\nDirection: {side_1}\nCoin size: {position_size_m1}\n{position_market_m1} Price: ${accept_price_m1}\nTrade PnL: ${unrealized_pnl_m1}\n\nTrade closed: {position_market_m2}\nDirection: {side_2}\nCoin size: {position_size_m2}\n{position_market_m2} Price: ${accept_price_m2}\nTrade PnL: ${unrealized_pnl_m2}\n\nLeverage used: {LEVERAGE}x\nAccount Balance: ${round(balance, 2)}')
                    except Exception as e:
                        print(
                            f'Exit failed for {position_market_m1} with {position_market_m2}, Error: {e}')
                        save_output.append(position)

                # Keep record if items and save
                else:
                    save_output.append(position)

            # Save remaining items
            print(f'{len(save_output)} Items remaining. Saving file...')
            with open('bot_agents.json', 'w') as f:
                json.dump(save_output, f)
    except Exception as e:
        print(f'Thread closed due to timeout, Error: {e}')
