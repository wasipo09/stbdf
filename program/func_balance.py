from func_connections import connect_dydx
from func_messaging import send_message_telegram
from decouple import config  # Python Library for env vars
import math
import threading


client = connect_dydx()
account = client.private.get_account(
    ethereum_address=config('ETH_ADDRESS'),
)

balance = float(account.data['account']['quoteBalance'])
free_collateral = float(account.data['account']['freeCollateral'])

LEVERAGE = 10
# STOP_LOSS_PERCENTAGE = 100 / LEVERAGE
STOP_LOSS_PERCENTAGE = 1 / 3

# 1% of our account for each trade with 10x leverage
USD_PER_TRADE = math.trunc((free_collateral / 100) * LEVERAGE)

# Maximum 50 trades open at the same time
USD_MIN_COLLATERAL = math.trunc(free_collateral / 2)


# Return balance and UnrealizedPnl every 3 hour
def check_balance():
    threading.Timer(10800, check_balance).start()

    # Check PnL
    position = client.private.get_positions(
        status='OPEN')

    all_positions = position.data['positions']
    unrealized_PnL = 0
    if len(all_positions):
        for x in range(len(all_positions)):
            unrealized_PnL += float(all_positions[x]['unrealizedPnl'])

    unrealized_PnL = round(unrealized_PnL, 2) if unrealized_PnL != 0 else 0

    send_message_telegram(
        f'Account Balance: ${round(balance, 2)}\nFree Collateral: ${round(free_collateral, 2)}\nLeverage Used: {LEVERAGE}x\nActive Trades: {len(all_positions)}\nUnrealized PnL: ${unrealized_PnL}')
