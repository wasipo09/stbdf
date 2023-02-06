from dydx3.constants import API_HOST_MAINNET, API_HOST_GOERLI
from decouple import config  # Python Library for env vars


# Token size must be a factor of 10, coins limitation
TOKEN_FACTOR_10 = ['XLM-USD', 'DOGE-USD', 'TRX-USD']

# !!!! SELECT MODE !!!!
# Available: MAINNET - TESTNET
MODE = 'MAINNET'

# Close all open positions and orders
ABORT_ALL_POSITIONS = False

# Find Cointegrated Pairs
FIND_COINTEGRATED = True

# Manage Exits
MANAGE_EXITS = False

# Place Trades
PLACE_TRADES = False

# Resolution, Test with others Timeframe.. add more data range into func_utils for lower timeframe
RESOLUTION = '1HOUR'

# Stats Window, Calculating the z-score, do a rolling moving average
# Standard Deviation of previous 21 hours, days.. based on the Timeframe
WINDOW = 21

# Thresholds - Opening
# Half Life: It's saying how long on average will it take for our spread to revert back, it's very useful because it helps us identify good looking spreads that will give us a higher probability of having profitable trades, Look for low half life, not negative, betweenn 0 and 25, half life is a great indicator for a spread that goes up and down.
# What I'm looking for is like an oscillating spread.
MAX_HALF_LIFE = 20
# It will Short / Long the first pair and Long / Short the second pair, lowering this value will make our strategy more aggressive and more trades will take place
ZSCORE_THRESH = 1.5
ZSCORE_CROSSING = 10
# USD_PER_TRADE = USD_PER_TRADE
# USD_MIN_COLLATERAL = USD_MIN_COLLATERAL

# Thresholds - Closing
CLOSE_AT_ZSCORE_CROSS = True

# Ethereum Address
ETHEREUM_ADDRESS = '0x768964bF90D157B33eA2495Dd97C40988C18A269'

# KEYS - MAINNET
# Must be on Mainnet in DYDX
STARK_PRIVATE_KEY_MAINNET = config('STARK_PRIVATE_KEY_MAINNET')
DYDX_API_KEY_MAINNET = config('DYDX_API_KEY_MAINNET')
DYDX_API_SECRET_MAINNET = config('DYDX_API_SECRET_MAINNET')
DYDX_API_PASSPHRASE_MAINNET = config('DYDX_API_PASSPHRASE_MAINNET')

# KEYS - TESTNET
# Must be on Testnet in DYDX
STARK_PRIVATE_KEY_TESTNET = config('STARK_PRIVATE_KEY_TESTNET')
DYDX_API_KEY_TESTNET = config('DYDX_API_KEY_TESTNET')
DYDX_API_SECRET_TESTNET = config('DYDX_API_SECRET_TESTNET')
DYDX_API_PASSPHRASE_TESTNET = config('DYDX_API_PASSPHRASE_TESTNET')

# KEYS - Export
STARK_PRIVATE_KEY = STARK_PRIVATE_KEY_MAINNET if MODE == 'MAINNET' else STARK_PRIVATE_KEY_TESTNET
DYDX_API_KEY = DYDX_API_KEY_MAINNET if MODE == 'MAINNET' else DYDX_API_KEY_TESTNET
DYDX_API_SECRET = DYDX_API_SECRET_MAINNET if MODE == 'MAINNET' else DYDX_API_SECRET_TESTNET
DYDX_API_PASSPHRASE = DYDX_API_PASSPHRASE_MAINNET if MODE == 'MAINNET' else DYDX_API_PASSPHRASE_TESTNET

# HOST - Export
HOST = API_HOST_MAINNET if MODE == 'MAINNET' else API_HOST_GOERLI

# HTTP PROVIDER
# Taken from Alchemy.com
HTTP_PROVIDER_MAINNET = "https://eth-mainnet.g.alchemy.com/v2/LZeIMgKepVjv9lkV-Y7B0mx9dKMKPfMl"
HTTP_PROVIDER_TESTNET = "https://eth-goerli.g.alchemy.com/v2/kvosk5u-FIAjB_Sv8lYvBOmMWSVx-nb9"
HTTP_PROVIDER = HTTP_PROVIDER_MAINNET if MODE == 'MAINNET' else HTTP_PROVIDER_TESTNET
