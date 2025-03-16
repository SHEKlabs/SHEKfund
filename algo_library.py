# algo_library.py - Trading Algorithm Library for SHEKfund

class OGBuySellThresholdAlgo:
    """Original threshold-based trading algorithm."""
    
    def __init__(self, buy_threshold=None, sell_threshold=None):
        """
        Initialize algorithm with optional buy and sell thresholds.
        
        Args:
            buy_threshold (float, optional): Initial price threshold for buying
            sell_threshold (float, optional): Initial price threshold for selling
        """
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        print(f"OGBuySellThresholdAlgo initialized with buy_threshold={buy_threshold}, sell_threshold={sell_threshold}")
        
        # Track last decision for debugging
        self.last_decision = None
        self.last_price = None
    
    def set_thresholds(self, buy_threshold, sell_threshold):
        """
        Update the buy and sell thresholds dynamically.
        
        Args:
            buy_threshold (float): New price threshold for buying
            sell_threshold (float): New price threshold for selling
        """
        if buy_threshold is None or sell_threshold is None:
            print(f"ERROR: Cannot set None thresholds. Buy: {buy_threshold}, Sell: {sell_threshold}")
            return
            
        old_buy = self.buy_threshold
        old_sell = self.sell_threshold
        
        # Store the new thresholds
        self.buy_threshold = float(buy_threshold)
        self.sell_threshold = float(sell_threshold)
        
        print(f"OGBuySellThresholdAlgo thresholds updated:")
        print(f"  Old: Buy=${old_buy if old_buy is not None else 'None'}, Sell=${old_sell if old_sell is not None else 'None'}")
        print(f"  New: Buy=${self.buy_threshold:.2f}, Sell=${self.sell_threshold:.2f}")
        
        # Validate thresholds were set correctly
        if self.buy_threshold != buy_threshold or self.sell_threshold != sell_threshold:
            print(f"ERROR: Threshold update failed! Expected buy={buy_threshold}, sell={sell_threshold}")
            print(f"Got buy={self.buy_threshold}, sell={self.sell_threshold}")
        else:
            print(f"OGBuySellThresholdAlgo threshold update CONFIRMED: buy=${buy_threshold:.2f}, sell=${sell_threshold:.2f}")
            
        # Check if buy is below sell
        if self.buy_threshold >= self.sell_threshold:
            print(f"WARNING: Buy threshold (${self.buy_threshold:.2f}) is >= Sell threshold (${self.sell_threshold:.2f})")
            print(f"This may lead to unexpected trading behavior!")
    
    def decide_trade(self, current_price, buy_threshold=None, sell_threshold=None, in_position=False):
        """
        Decide whether to buy, sell, or hold based on thresholds.
        
        Args:
            current_price (float): Current price of the asset
            buy_threshold (float, optional): Price threshold for buying (overrides instance variable)
            sell_threshold (float, optional): Price threshold for selling (overrides instance variable)
            in_position (bool): Whether we currently hold a position
            
        Returns:
            str: 'buy', 'sell', or 'hold'
        """
        # Track current price for debugging
        self.last_price = current_price
        
        # Use provided thresholds or fall back to instance variables
        buy_threshold = buy_threshold if buy_threshold is not None else self.buy_threshold
        sell_threshold = sell_threshold if sell_threshold is not None else self.sell_threshold
        
        # Ensure thresholds are set before making decisions
        if buy_threshold is None or sell_threshold is None:
            print(f"OGBuySellThresholdAlgo: Cannot make decision - thresholds not set (buy: {buy_threshold}, sell: {sell_threshold})")
            self.last_decision = "hold"
            return "hold"
            
        # Print debug information for every decision
        print(f"OGBuySellThresholdAlgo DECISION PROCESS:")
        print(f"  Current price: ${current_price:.2f}")
        print(f"  Buy threshold: ${buy_threshold:.2f}")
        print(f"  Sell threshold: ${sell_threshold:.2f}")
        print(f"  Position status: {'IN POSITION' if in_position else 'NOT IN POSITION'}")
        
        # Check for buy signal - when price is at or below buy threshold and not in position
        if not in_position and current_price <= buy_threshold:
            print(f"OGBuySellThresholdAlgo: BUY SIGNAL - price ${current_price:.2f} <= buy threshold ${buy_threshold:.2f}")
            self.last_decision = "buy"
            return "buy"
            
        # Check for sell signal - when price is at or above sell threshold and in position
        elif in_position and current_price >= sell_threshold:
            print(f"OGBuySellThresholdAlgo: SELL SIGNAL - price ${current_price:.2f} >= sell threshold ${sell_threshold:.2f}")
            self.last_decision = "sell"
            return "sell"
            
        else:
            # Log exactly why we're holding
            if in_position:
                print(f"OGBuySellThresholdAlgo: HOLD - price ${current_price:.2f} has not reached sell threshold ${sell_threshold:.2f}")
                print(f"  Waiting for price to rise by ${sell_threshold - current_price:.2f} to trigger sell")
            else:
                print(f"OGBuySellThresholdAlgo: HOLD - price ${current_price:.2f} has not reached buy threshold ${buy_threshold:.2f}")
                print(f"  Waiting for price to fall by ${current_price - buy_threshold:.2f} to trigger buy")
                
            self.last_decision = "hold"
            return "hold"


class MovingAverageAlgo:
    """Trading algorithm based on moving averages crossing."""
    
    def __init__(self):
        """Initialize the algorithm with empty price history."""
        self.price_history = []
        self.short_window = 5
        self.long_window = 20
    
    def update_price_history(self, price):
        """Add a new price point to history and maintain size."""
        self.price_history.append(price)
        # Keep only the most recent prices needed for calculations
        max_needed = max(self.short_window, self.long_window)
        if len(self.price_history) > max_needed:
            self.price_history = self.price_history[-max_needed:]
    
    def calculate_moving_average(self, window):
        """Calculate moving average for the given window size."""
        if len(self.price_history) < window:
            return None
        return sum(self.price_history[-window:]) / window
    
    def decide_trade(self, current_price, buy_threshold, sell_threshold, in_position):
        """
        Decide trade based on moving average crossover.
        
        Args:
            current_price (float): Current price of the asset
            buy_threshold (float): Not used in this algorithm but kept for interface consistency
            sell_threshold (float): Not used in this algorithm but kept for interface consistency
            in_position (bool): Whether we currently hold a position
            
        Returns:
            str: 'buy', 'sell', or 'hold'
        """
        # Add current price to history
        self.update_price_history(current_price)
        
        # Calculate moving averages
        short_ma = self.calculate_moving_average(self.short_window)
        long_ma = self.calculate_moving_average(self.long_window)
        
        # Not enough data points yet
        if short_ma is None or long_ma is None:
            return "hold"
        
        # Buy signal: Short MA crosses above Long MA
        if not in_position and short_ma > long_ma:
            return "buy"
        # Sell signal: Short MA crosses below Long MA
        elif in_position and short_ma < long_ma:
            return "sell"
        else:
            return "hold"


# Dictionary mapping algorithm names to their classes
ALGO_LIBRARY = {
    "OG_buy_sell_threshold_algo": OGBuySellThresholdAlgo,
    "Moving_average_algo": MovingAverageAlgo,
    # Add more algorithms here as needed
} 