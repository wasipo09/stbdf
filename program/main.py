from constants import ABORT_ALL_POSITIONS, FIND_COINTEGRATED, PLACE_TRADES, MANAGE_EXITS
from func_connections import connect_dydx
from func_private import abort_all_positions
from func_public import construct_market_prices
from func_cointegration import store_cointegration_results
from func_entry_pairs import open_positions
from func_exit_pairs import manage_trade_exits
from func_balance import balance, check_balance
from func_messaging import send_message_telegram

from multiprocessing import Process
from threading import Thread, Timer


# MAIN FUNCTION
if __name__ == '__main__':

    # Message on start
    send_message_telegram(
        f'DYDX Bot launched successfully\n\nAccount Balance: ${round(balance, 2)}')

    # Connect to client
    try:
        print('Connecting to Client...')
        client = connect_dydx()
    except Exception as e:
        print('Error connecting to client: ', e)
        send_message_telegram(f'Failed to connect to client, {e}')
        exit(1)

    # Abort all open positions
    if ABORT_ALL_POSITIONS:
        try:
            print('Closing all positions...')
            close_orders = abort_all_positions(client)
        except Exception as e:
            print('Error closing all positions: ', e)
            send_message_telegram(f'Error closing all positions, {e}')
            exit(1)

    # Find Cointegrated Pairs
    if FIND_COINTEGRATED:
        def find_cointegrated():
            # Fetch market prices and update csv file every 24 hours
            Timer(86400, find_cointegrated).start()
            # Construct Market Prices
            try:
                print('Fetching market prices, please allow 3 mins...')
                df_market_prices = construct_market_prices(client)
            except Exception as e:
                print('Error constructing market prices: ', e)
                send_message_telegram(f'Error constructing market prices, {e}')
                exit(1)

            # Store Cointegrated Pairs
            try:
                print('Storing cointegrated pairs...')
                stores_result = store_cointegration_results(df_market_prices)
                if stores_result != 'saved':
                    print('Error saving cointegrated pairs')
                    exit(1)
            except Exception as e:
                print('Error saving cointegrated pairs: ', e)
                send_message_telegram(f'Error saving cointegrated pairs, {e}')
                exit(1)

        find_cointegrated()

    # Send balance through telegram
    check_balance()

    # Run as always on and simultaneously
    #t1 = Thread(target=manage_trade_exits, args=(client,))
    t2 = Thread(target=open_positions, args=(client,))
    #t1.start()
    t2.start()
    #t1.join(timeout=10)
    t2.join(timeout=10)

    # Run as always on
    # while True:
    # Place trades for opening positions
    # if MANAGE_EXITS:
    #     try:
    #         # print('Managing exits...')
    #         Process(target=manage_trade_exits(client)).start()
    #         # manage_trade_exits(client)
    #     except Exception as e:
    #         print('Error managing exiting positions: ', e)
    #         send_message_telegram(
    #             f'Error managing exiting positions, {e}')
    #         exit(1)

    # # Place trades for opening positions
    # if PLACE_TRADES:
    #     try:
    #         # print('Finding trading opportunities...')
    #         Process(target=open_positions(client)).start()
    #         # open_positions(client)
    #     except Exception as e:
    #         print('Error trading pairs: ', e)
    #         send_message_telegram(f'Error opening trades, {e}')
    #         exit(1)
