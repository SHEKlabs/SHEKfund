import time
import threading
import config

class ChartManager:
    """Class to manage chart data, including price history and trade markers"""
    
    def __init__(self):
        """Initialize chart data containers"""
        self.price_history = []  # List of [timestamp, price]
        self.buy_trades = []     # List of [timestamp, price] for buys
        self.sell_trades = []    # List of [timestamp, price] for sells
        self.thresholds = {}     # Dictionary with 'buy' and 'sell' thresholds
        self.current_symbol = "" # Currently selected symbol for trading
        self.lock = threading.Lock()  # For thread-safe data access
        
    def set_symbol_and_thresholds(self, symbol, buy_threshold, sell_threshold):
        """Set the current symbol and trading thresholds"""
        with self.lock:
            self.current_symbol = symbol
            self.thresholds = {'buy': buy_threshold, 'sell': sell_threshold}
            
    def clear_data(self):
        """Clear all chart data - useful when switching coins"""
        with self.lock:
            self.price_history = []
            self.buy_trades = []
            self.sell_trades = []
            
    def add_price_point(self, price, timestamp=None):
        """Add a price point to the history"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)  # Current time in milliseconds
            
        with self.lock:
            self.price_history.append([timestamp, price])
            # Limit history size to prevent memory issues
            if len(self.price_history) > config.MAX_PRICE_HISTORY:
                self.price_history = self.price_history[-config.MAX_PRICE_HISTORY:]
                
    def add_buy_trade(self, price, timestamp=None):
        """Record a buy trade"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
            
        with self.lock:
            self.buy_trades.append([timestamp, price])
            
    def add_sell_trade(self, price, timestamp=None):
        """Record a sell trade"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
            
        with self.lock:
            self.sell_trades.append([timestamp, price])
            
    def get_chart_data(self):
        """Get all chart data for the web interface"""
        with self.lock:
            data = {
                'symbol': self.current_symbol,
                'price_history': self.price_history[:],
                'buy_trades': self.buy_trades[:],
                'sell_trades': self.sell_trades[:],
                'thresholds': self.thresholds.copy()
            }
        return data 