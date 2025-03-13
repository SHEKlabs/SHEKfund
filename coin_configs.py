# Coin configurations for SHEKfund Trading Bot
# This file contains the list of available coins and their trading parameters

# Available coins for trading
AVAILABLE_COINS = ['BTCUSDT', 'ETHUSDT', 'LTCUSDT']

# Configuration for each coin with buy/sell thresholds and quantities
COIN_CONFIGS = {
    'BTCUSDT': {
        'buy_threshold': 85985, 
        'sell_threshold': 85990, 
        'quantity': 0.001
    },
    'ETHUSDT': {
        'buy_threshold': 3000, 
        'sell_threshold': 3100, 
        'quantity': 0.01
    },
    'LTCUSDT': {
        'buy_threshold': 150, 
        'sell_threshold': 160, 
        'quantity': 0.1
    }
}

# You can add more coins by adding to AVAILABLE_COINS list and
# adding corresponding configuration in the COIN_CONFIGS dictionary 