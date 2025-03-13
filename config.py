# Configuration file for SHEKfund Trading Bot
from coin_configs import AVAILABLE_COINS, COIN_CONFIGS

# API credentials
API_KEY = 'vUB2Zptz3Xnu77rAyEkqU2AURgG1G9h29Kx22uxShCIZBepRznjBq3yfd1kYYAoG'
API_SECRET_KEY = 'aeDTMXgEZYVm52EbQ9CFl6yk5pSawd6WSxCU2dPirBAqQyEPQXrr9G8YDTcQxtBO'
USE_TESTNET = True  # Set to False for real trading

# Time intervals (in seconds)
PRICE_CHECK_INTERVAL = 1.5  # How often to check price
CHART_UPDATE_INTERVAL = 1.0  # How often the chart refreshes

# Web server settings
HOST = '0.0.0.0'
PORT = 5000
DEBUG = False
USE_RELOADER = False
FLASK_QUIET = True  # Set to True to suppress Flask logs
FLASK_LOG_LEVEL = 'ERROR'  # Set to 'ERROR' to only show errors, 'INFO' for more details

# Chart settings
MAX_PRICE_HISTORY = 1000  # Maximum number of points to keep in price history 