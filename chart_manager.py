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
        self.trade_log = []      # Detailed trade log for the table display
        self.thresholds = {}     # Dictionary with 'buy' and 'sell' thresholds
        self.current_symbol = "" # Currently selected symbol for trading
        self.lock = threading.Lock()  # For thread-safe data access
        
        # P&L tracking
        self.open_positions = []  # List of {"buy_price": float, "amount": float, "timestamp": int}
        self.net_invested = 0.0   # USD - Total amount invested in open positions
        self.cumulative_profit = 0.0  # USD - Total profit/loss from all completed trades
        
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
            self.trade_log = []
            self.open_positions = []
            self.net_invested = 0.0
            self.cumulative_profit = 0.0
            
    def add_price_point(self, price, timestamp=None):
        """Add a price point to the history"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)  # Current time in milliseconds
            
        with self.lock:
            self.price_history.append([timestamp, price])
            # Limit history size to prevent memory issues
            if len(self.price_history) > config.MAX_PRICE_HISTORY:
                self.price_history = self.price_history[-config.MAX_PRICE_HISTORY:]
                
    def add_buy_trade(self, price, quantity, timestamp=None, threshold_triggered=False):
        """Record a buy trade with detailed information"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        
        # Calculate dollar amount
        dollar_amount = price * quantity
            
        with self.lock:
            # P&L tracking - Add to open positions
            self.open_positions.append({
                "buy_price": price, 
                "amount": quantity, 
                "timestamp": timestamp
            })
            self.net_invested += dollar_amount
            
            # Add to basic buy trades for chart
            self.buy_trades.append([timestamp, price])
            
            # Create detailed trade entry
            threshold_info = "Buy threshold triggered" if threshold_triggered else ""
            description = f"Bought {quantity} {self.current_symbol[:-4]} at ${price:.2f}. {threshold_info}"
            
            trade_details = {
                "time": timestamp,
                "price": price,
                "amount": quantity,
                "dollar_amount": dollar_amount,
                "type": "buy",
                "description": description,
                "profit": self.cumulative_profit,  # Record current cumulative profit (not changing on buy)
                "net_invested": self.net_invested,
                "coin": self.current_symbol[:-4]  # Store coin symbol without USDT suffix
            }
            
            # Add to trade log
            self.trade_log.append(trade_details)
            
    def add_sell_trade(self, price, quantity, timestamp=None, threshold_triggered=False):
        """Record a sell trade with detailed information"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)
        
        # Calculate dollar amount
        dollar_amount = price * quantity
        
        # Calculate profit using FIFO method for this specific trade
        trade_profit = 0.0
        remaining_sell = quantity
        
        with self.lock:
            # Process sells using FIFO logic
            while remaining_sell > 0 and self.open_positions:
                position = self.open_positions[0]  # Get oldest position
                
                if position["amount"] <= remaining_sell:
                    # Sell entire position
                    sold_amount = position["amount"]
                    position_profit = (price - position["buy_price"]) * sold_amount
                    self.net_invested -= position["buy_price"] * sold_amount
                    remaining_sell -= sold_amount
                    self.open_positions.pop(0)  # Remove the fully sold position
                else:
                    # Partially sell position
                    sold_amount = remaining_sell
                    position_profit = (price - position["buy_price"]) * sold_amount
                    self.net_invested -= position["buy_price"] * sold_amount
                    position["amount"] -= sold_amount  # Reduce position amount
                    remaining_sell = 0
                
                trade_profit += position_profit
            
            # Update cumulative profit with this trade's profit/loss
            self.cumulative_profit += trade_profit
            
            # Add to basic sell trades for chart
            self.sell_trades.append([timestamp, price])
            
            # Create detailed trade entry
            threshold_info = "Sell threshold triggered" if threshold_triggered else ""
            description = f"Sold {quantity} {self.current_symbol[:-4]} at ${price:.2f}. {threshold_info}"
            
            # For individual trade profit display (if needed later)
            individual_trade_profit = trade_profit
            
            trade_details = {
                "time": timestamp,
                "price": price,
                "amount": quantity,
                "dollar_amount": dollar_amount,
                "type": "sell",
                "description": description,
                "profit": self.cumulative_profit,  # Store updated cumulative profit
                "individual_trade_profit": individual_trade_profit,  # Store individual trade profit for reference
                "net_invested": self.net_invested,
                "coin": self.current_symbol[:-4]  # Store coin symbol without USDT suffix
            }
            
            # Add to trade log
            self.trade_log.append(trade_details)
            
    def get_chart_data(self):
        """Get all chart data for the web interface"""
        with self.lock:
            data = {
                'symbol': self.current_symbol,
                'price_history': self.price_history[:],
                'buy_trades': self.buy_trades[:],
                'sell_trades': self.sell_trades[:],
                'thresholds': self.thresholds.copy(),
                'trade_log': self.trade_log[:],  # Include trade log in the response
                'net_invested': self.net_invested,
                'cumulative_profit': self.cumulative_profit
            }
        return data 