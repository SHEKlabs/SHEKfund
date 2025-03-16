import time
import os
from datetime import datetime
import config
import threading

class TradingBot:
    """Class to handle trading logic and execution"""
    
    def __init__(self, data_fetcher, chart_manager, algorithm=None, algorithm_name="OG_buy_sell_threshold_algo"):
        """Initialize with dependencies"""
        self.data_fetcher = data_fetcher
        self.chart_manager = chart_manager
        self.algorithm = algorithm
        self.algorithm_name = algorithm_name
        self.in_position = False
        self.last_action = "None"
        self.running = False
        self.buy_threshold = None
        self.sell_threshold = None
        self.last_price_check = 0  # Track when we last checked the price
        self.pending_check = False  # Flag to force a price check after threshold updates
        self.force_check = False  # Flag to force immediate check
        
        # Add thread synchronization lock
        self.trade_lock = threading.Lock()
        # Add a state lock for position updates
        self.state_lock = threading.Lock()
        
    def update_display(self, symbol, current_price, buy_threshold, sell_threshold):
        """Update the terminal display with current status"""
        # Get the position state in a thread-safe way
        with self.state_lock:
            in_position = self.in_position
            last_action = self.last_action
            
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear console
        print("~~~~ SHEKfund Trading Bot ~~~~")
        print(f"Selected Coin: {symbol}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"Buy Threshold: ${buy_threshold:.2f}")
        print(f"Sell Threshold: ${sell_threshold:.2f}")
        print(f"Position Status: {'In Position' if in_position else 'Not In Position'}")
        print(f"Last Action: {last_action}")
        print(f"Algorithm: {self.algorithm_name}")
        print(f"Web Interface: http://localhost:{config.PORT}")
        print("Press Ctrl+C to exit")
        print("----------------------------")
        now = datetime.now()
        formatted_date_time = now.strftime("< %d-%m-%Y | %H:%M:%S >")
        print(f"Last updated: {formatted_date_time}")
    
    def get_algorithm_name(self):
        """Return the current algorithm name"""
        return self.algorithm_name
    
    def get_current_thresholds(self, use_lock=True):
        """Return the current buy and sell thresholds with improved validation"""
        # Optionally acquire lock to ensure consistent threshold readings
        if use_lock:
            self.trade_lock.acquire()
        
        try:
            # First check if algorithm has thresholds
            algo_buy = None
            algo_sell = None
            
            if self.algorithm and hasattr(self.algorithm, 'buy_threshold') and hasattr(self.algorithm, 'sell_threshold'):
                algo_buy = self.algorithm.buy_threshold
                algo_sell = self.algorithm.sell_threshold
            
            # If algo thresholds exist, use them, otherwise use bot's internal thresholds
            buy_threshold = algo_buy if algo_buy is not None else self.buy_threshold
            sell_threshold = algo_sell if algo_sell is not None else self.sell_threshold
            
            # Log the thresholds for debugging
            print(f"Current Thresholds - Buy: ${buy_threshold if buy_threshold is not None else 'None'}, "
                  f"Sell: ${sell_threshold if sell_threshold is not None else 'None'}")
            
            return {
                'buy': buy_threshold,
                'sell': sell_threshold
            }
        finally:
            # Release the lock if we acquired it
            if use_lock:
                self.trade_lock.release()
    
    def update_thresholds(self, buy_threshold=None, sell_threshold=None):
        """Update buy and sell thresholds for the trading bot."""
        # Acquire lock for thread safety during threshold updates
        with self.trade_lock:
            # Record old values for logging
            old_buy_threshold = self.buy_threshold
            old_sell_threshold = self.sell_threshold
            
            # Update bot's local thresholds
            if buy_threshold is not None:
                self.buy_threshold = buy_threshold
            if sell_threshold is not None:
                self.sell_threshold = sell_threshold
            
            # Update algorithm's thresholds if supported
            if hasattr(self.algorithm, 'set_thresholds') and callable(self.algorithm.set_thresholds):
                try:
                    self.algorithm.set_thresholds(buy_threshold=buy_threshold, sell_threshold=sell_threshold)
                    print(f"✅ Algorithm thresholds updated: buy={buy_threshold}, sell={sell_threshold}")
                except Exception as e:
                    print(f"⚠️ Warning: Failed to update algorithm thresholds: {e}")
            else:
                print(f"⚠️ Warning: Algorithm does not support updating thresholds, only bot's internal thresholds updated")
            
            # Notify chart manager of threshold change
            if self.chart_manager:
                self.chart_manager.update_thresholds({
                    'buy': self.buy_threshold,
                    'sell': self.sell_threshold,
                    'timestamp': time.time()
                })
            
            print(f"Threshold update: {old_buy_threshold} → {self.buy_threshold} (buy), {old_sell_threshold} → {self.sell_threshold} (sell)")
            
            # Force an immediate price check after threshold update with high priority flags
            self.force_check = True
            self.last_price_check = 0  # Reset last check time to force immediate check
            self.pending_check = True  # Set flag for pending check
            
            # Store the current thresholds to return
            current_thresholds = {
                'buy': self.buy_threshold,
                'sell': self.sell_threshold,
                'force_check': self.force_check
            }
        
        # IMPORTANT: Execute immediate trade check outside of the lock
        # Attempt up to 3 immediate trade checks to ensure the change takes effect
        max_immediate_checks = 3
        check_interval = 0.5  # seconds
        trade_check_succeeded = False
        
        if self.data_fetcher and self.data_fetcher.current_symbol and hasattr(self, 'running') and self.running:
            for attempt in range(max_immediate_checks):
                try:
                    # Get a fresh price for each attempt
                    current_price = self.data_fetcher.get_current_price(self.data_fetcher.current_symbol, force_fresh=True)
                    if current_price is None:
                        print(f"⚠️ Attempt {attempt+1}/{max_immediate_checks}: Could not get current price, trying again...")
                        time.sleep(check_interval)
                        continue
                    
                    # Get coin configuration for quantity
                    from coin_configs import COIN_CONFIGS
                    coin_config = COIN_CONFIGS.get(self.data_fetcher.current_symbol, {})
                    quantity = coin_config.get('quantity', 0.001)  # Default quantity if not found
                    
                    print(f"🔄 Immediate trade check attempt {attempt+1}/{max_immediate_checks} with new thresholds - Price: ${current_price}")
                    
                    # Check if the price is already beyond threshold (to provide better logging)
                    with self.state_lock:
                        in_position = self.in_position
                    
                    threshold_breached = False
                    with self.trade_lock:
                        if not in_position and current_price <= self.buy_threshold:
                            print(f"💡 THRESHOLD BREACH DETECTED: Price ${current_price:.2f} <= Buy ${self.buy_threshold:.2f}")
                            threshold_breached = True
                        elif in_position and current_price >= self.sell_threshold:
                            print(f"💡 THRESHOLD BREACH DETECTED: Price ${current_price:.2f} >= Sell ${self.sell_threshold:.2f}")
                            threshold_breached = True
                    
                    # Execute the trade check
                    result = self.check_and_execute_trades(self.data_fetcher.current_symbol, current_price, quantity, skip_lock=True)
                    
                    if result:
                        print(f"✅ Trade successfully executed on immediate check #{attempt+1}")
                        trade_check_succeeded = True
                        break
                    elif threshold_breached:
                        # If threshold was breached but no trade executed, try again immediately
                        print(f"⚠️ Threshold breached but no trade executed on attempt {attempt+1}")
                        # Wait a moment before trying again
                        time.sleep(check_interval)
                    else:
                        # If no threshold breach, just log and we're done
                        print(f"ℹ️ No threshold breach detected on attempt {attempt+1}, trade check complete")
                        trade_check_succeeded = True  # Mark as success since check completed normally
                        break
                        
                except Exception as e:
                    print(f"⚠️ Error during immediate trade check attempt {attempt+1}: {e}")
                    # Wait a moment before trying again
                    time.sleep(check_interval)
        
        # Set flag for the main loop to double-check even if our immediate checks succeeded
        # This provides a backup in case the immediate check missed anything
        with self.trade_lock:
            # Only set pending_check if our attempts didn't succeed
            if not trade_check_succeeded:
                self.pending_check = True
                print("Immediate trade checks failed or not attempted. Ensuring next main loop iteration will perform check.")
            else:
                # Even if successful, let's do one more check in the main loop for safety
                self.pending_check = True
                print("Immediate trade checks successful, but scheduling one more check in the main loop for safety")
        
        # Verify that both algorithm's and bot's local thresholds are set correctly
        if hasattr(self.algorithm, 'buy_threshold') and hasattr(self.algorithm, 'sell_threshold'):
            if self.algorithm.buy_threshold != self.buy_threshold or self.algorithm.sell_threshold != self.sell_threshold:
                print(f"⚠️ Warning: Threshold mismatch between bot and algorithm!")
                print(f"  Bot: buy={self.buy_threshold}, sell={self.sell_threshold}")
                print(f"  Algo: buy={self.algorithm.buy_threshold}, sell={self.algorithm.sell_threshold}")
        
        print(f"Next price check will use thresholds: buy={self.buy_threshold}, sell={self.sell_threshold}")
        print(f"Forced immediate check after threshold update: {self.force_check}")
        print(f"Pending check flag: {self.pending_check}")
        
        return current_thresholds
    
    def check_and_execute_trades(self, symbol, current_price, quantity, skip_lock=False):
        """
        Check if current price crosses thresholds and execute trades if needed.
        Centralized function to handle trade execution based on thresholds.
        
        Args:
            symbol: The cryptocurrency symbol
            current_price: Current price of the cryptocurrency
            quantity: Quantity to trade
            skip_lock: If True, skip acquiring the trade_lock (used when called from update_thresholds)
        
        Returns: True if a trade was executed, False otherwise
        """
        # Function to process trading logic - extracted to avoid duplicate code
        def process_trading_logic():
            # Ensure price and thresholds are valid
            if current_price is None:
                print("Cannot check trades - current price is None")
                return False

            # Get current thresholds without acquiring the lock again
            current_thresholds = self.get_current_thresholds(use_lock=False)
            buy_threshold = current_thresholds['buy']
            sell_threshold = current_thresholds['sell']

            if buy_threshold is None or sell_threshold is None:
                print("Thresholds not set - cannot proceed with trade decisions")
                return False
            
            # Log current state for debugging
            print(f"\n=== TRADE CHECK at {time.strftime('%H:%M:%S')} ===")
            print(f"Symbol: {symbol}, Price: ${current_price:.2f}, Buy Threshold: ${buy_threshold:.2f}, Sell Threshold: ${sell_threshold:.2f}")
            
            # Get position state in a thread-safe way
            with self.state_lock:
                in_position = self.in_position
            
            print(f"In Position: {in_position}")
            
            # If algorithm is set, use it to make trade decisions
            if self.algorithm and hasattr(self.algorithm, 'decide_trade') and callable(self.algorithm.decide_trade):
                try:
                    decision = self.algorithm.decide_trade(
                        current_price=current_price,
                        buy_threshold=buy_threshold,
                        sell_threshold=sell_threshold,
                        in_position=in_position
                    )
                    print(f"Algorithm decision: {decision}")
                    
                    if decision == "buy" and not in_position:
                        print(f"BUY SIGNAL FROM ALGORITHM: Price ${current_price:.2f}, Buy Threshold ${buy_threshold:.2f}")
                        # Release the trade_lock before executing buy to prevent deadlocks
                        if not skip_lock:
                            self.trade_lock.release()
                        try:
                            return self._execute_buy(symbol, quantity, current_price, f"{self.algorithm_name} buy decision")
                        finally:
                            # Re-acquire the lock if we were skipping and had released it
                            if not skip_lock:
                                self.trade_lock.acquire()
                    elif decision == "sell" and in_position:
                        print(f"SELL SIGNAL FROM ALGORITHM: Price ${current_price:.2f}, Sell Threshold ${sell_threshold:.2f}")
                        # Release the trade_lock before executing sell to prevent deadlocks
                        if not skip_lock:
                            self.trade_lock.release()
                        try:
                            return self._execute_sell(symbol, quantity, current_price, f"{self.algorithm_name} sell decision")
                        finally:
                            # Re-acquire the lock if we were not skipping and had released it
                            if not skip_lock:
                                self.trade_lock.acquire()
                    else:
                        print(f"NO TRADE: Algorithm decided to {decision}")
                        return False
                except Exception as e:
                    print(f"Error using algorithm for decision: {e}")
                    print("Falling back to simple threshold logic")
                    # Fall through to the threshold-based logic below
            
            # Fallback simple threshold logic if no algorithm or algorithm fails
            # Buy logic: Execute buy if price <= buy threshold and not in position
            if not in_position and current_price <= buy_threshold:
                print(f"BUY SIGNAL DETECTED: Price ${current_price:.2f} <= Buy Threshold ${buy_threshold:.2f}")
                # Release the trade_lock before executing buy to prevent deadlocks
                if not skip_lock:
                    self.trade_lock.release()
                try:
                    return self._execute_buy(symbol, quantity, current_price, "OG_buy_sell_threshold_algo buy trigger")
                finally:
                    # Re-acquire the lock if we were not skipping and had released it
                    if not skip_lock:
                        self.trade_lock.acquire()
            # Sell logic: Execute sell if price >= sell threshold and in position
            elif in_position and current_price >= sell_threshold:
                print(f"SELL SIGNAL DETECTED: Price ${current_price:.2f} >= Sell Threshold ${sell_threshold:.2f}")
                # Release the trade_lock before executing sell to prevent deadlocks
                if not skip_lock:
                    self.trade_lock.release()
                try:
                    return self._execute_sell(symbol, quantity, current_price, "OG_buy_sell_threshold_algo sell trigger")
                finally:
                    # Re-acquire the lock if we were not skipping and had released it
                    if not skip_lock:
                        self.trade_lock.acquire()
            else:
                if not in_position:
                    print(f"NO TRADE: Price ${current_price:.2f} > Buy Threshold ${buy_threshold:.2f} - Waiting for price to drop")
                else:
                    print(f"NO TRADE: Price ${current_price:.2f} < Sell Threshold ${sell_threshold:.2f} - Waiting for price to rise")
                return False
        
        # Main execution flow with proper lock management
        if skip_lock:
            # Skip acquiring the lock if we're called from a method that already holds it
            return process_trading_logic()
        else:
            # Acquire trade lock to ensure thread safety during trading decisions
            with self.trade_lock:
                return process_trading_logic()
    
    def start_trading(self, symbol, buy_threshold, sell_threshold, quantity):
        """Start the trading loop for a specific coin"""
        # Set up initial state
        self.running = True
        self.in_position = False
        self.last_action = "None"
        
        print(f"\n========== STARTING TRADING ==========")
        print(f"Starting to trade {symbol} with {self.algorithm_name}")
        
        # Initialize thresholds
        print(f"Setting initial thresholds: Buy=${buy_threshold:.2f}, Sell=${sell_threshold:.2f}")
        self.update_thresholds(buy_threshold, sell_threshold)
        
        # Configure chart manager
        self.chart_manager.set_symbol_and_thresholds(symbol, buy_threshold, sell_threshold)
        self.chart_manager.clear_data()
        
        # Start continuous price fetching
        print(f"Starting continuous price fetching for {symbol}")
        self.data_fetcher.start_price_fetching(symbol)
        
        # Get initial price and update display
        max_retries = 5
        current_price = None
        
        # Try several times to get the initial price
        for attempt in range(max_retries):
            print(f"Attempt {attempt+1}/{max_retries} to fetch initial price...")
            current_price = self.data_fetcher.get_current_price(symbol, force_fresh=True)
            if current_price is not None:
                print(f"Initial price retrieved: ${current_price:.2f}")
                break
            print(f"Attempt {attempt+1}/{max_retries}: Could not fetch initial price for {symbol}, retrying...")
            time.sleep(1)
            
        if current_price is None:
            print(f"Error: Could not fetch initial price for {symbol} after {max_retries} attempts")
            return
            
        # Add initial price point to chart
        self.chart_manager.add_price_point(current_price)
        
        # Initial display update
        self.update_display(symbol, current_price, buy_threshold, sell_threshold)
        
        # Log trading start
        print(f"\n========== TRADING STARTED ==========")
        print(f"Trading {symbol} with {self.algorithm_name} algorithm")
        print(f"Initial price: ${current_price}")
        print(f"Buy threshold: ${buy_threshold}")
        print(f"Sell threshold: ${sell_threshold}")
        print(f"Quantity: {quantity}")
        print(f"======================================\n")
        
        # Immediately check if we should execute a trade based on initial price
        print(f"Checking for immediate trade opportunity at startup...")
        trade_executed = self.check_and_execute_trades(symbol, current_price, quantity)
        if trade_executed:
            print(f"Initial trade executed at startup based on price ${current_price:.2f}")
        else:
            print(f"No immediate trade opportunities at startup.")
        
        # Keep track of last successful update time
        last_successful_update = time.time()
        consecutive_errors = 0
        
        # Main trading loop
        try:
            while self.running:
                try:
                    # Get the latest price data
                    latest_data = self.data_fetcher.get_latest_data()
                    current_price = latest_data.get("price")
                    
                    if current_price is None:
                        consecutive_errors += 1
                        print(f"No price data available. Waiting... (attempts: {consecutive_errors})")
                        
                        # If we haven't had a successful update in 30 seconds, try restarting price fetching
                        if time.time() - last_successful_update > 30:
                            print("Price updates stalled. Restarting price fetching...")
                            self.data_fetcher.stop_price_fetching()
                            time.sleep(1)
                            self.data_fetcher.start_price_fetching(symbol)
                            last_successful_update = time.time()  # Reset the timer
                            
                        time.sleep(config.PRICE_CHECK_INTERVAL)
                        continue
                    
                    # Reset error counter and update success time
                    consecutive_errors = 0
                    last_successful_update = time.time()
                    
                    # Record price point for chart
                    self.chart_manager.add_price_point(current_price)
                    
                    # Get current thresholds
                    current_thresholds = self.get_current_thresholds()
                    buy_threshold = current_thresholds['buy']
                    sell_threshold = current_thresholds['sell']
                    
                    # Force a price check if pending_check is set (after threshold update) 
                    # or if it's been more than 5 seconds
                    current_time = time.time()
                    check_needed = False
                    check_due_to_threshold_update = False
                    
                    # If a threshold update is pending, prioritize immediate check
                    if self.pending_check:
                        print(f"\n*** IMMEDIATE TRADE CHECK TRIGGERED BY THRESHOLD UPDATE ***")
                        print(f"Current price: ${current_price:.2f}, Buy threshold: ${buy_threshold:.2f}, Sell threshold: ${sell_threshold:.2f}")
                        check_needed = True
                        check_due_to_threshold_update = True
                        
                        # Check for threshold breach for additional logging
                        with self.state_lock:
                            in_position = self.in_position
                        
                        if not in_position and current_price <= buy_threshold:
                            print(f"⚠️ POSSIBLE BUY CONDITION DETECTED: Price ${current_price:.2f} <= Buy ${buy_threshold:.2f}")
                        elif in_position and current_price >= sell_threshold:
                            print(f"⚠️ POSSIBLE SELL CONDITION DETECTED: Price ${current_price:.2f} >= Sell ${sell_threshold:.2f}")
                        
                        # Don't reset the flag until after the check completes successfully
                    # Otherwise check based on time interval
                    elif (current_time - self.last_price_check >= 5):
                        check_needed = True
                    
                    # Execute trade check if needed
                    if check_needed:
                        try:
                            print(f"Executing trade check at {time.strftime('%H:%M:%S')}")
                            
                            # For threshold-triggered checks, make multiple rapid attempts
                            if check_due_to_threshold_update:
                                # Get a fresh price first
                                fresh_price = self.data_fetcher.get_current_price(symbol, force_fresh=True)
                                if fresh_price is not None:
                                    current_price = fresh_price
                                    print(f"Updated to fresh price: ${current_price:.2f} for threshold check")
                                
                                # Execute the first check
                                trade_executed = self.check_and_execute_trades(symbol, current_price, quantity)
                                self.last_price_check = current_time
                                
                                # If no trade executed but conditions should be right, try again
                                if not trade_executed:
                                    with self.state_lock:
                                        in_position = self.in_position
                                    
                                    if (not in_position and current_price <= buy_threshold) or \
                                       (in_position and current_price >= sell_threshold):
                                        
                                        print(f"⚠️ Trade conditions met but no trade executed. Trying again...")
                                        # Wait a moment and try once more with a fresh price
                                        time.sleep(0.5)
                                        
                                        # Get fresh price for second attempt
                                        fresh_price = self.data_fetcher.get_current_price(symbol, force_fresh=True)
                                        if fresh_price is not None:
                                            current_price = fresh_price
                                            print(f"Updated to fresh price for second attempt: ${current_price:.2f}")
                                        
                                        # Try again
                                        trade_executed = self.check_and_execute_trades(symbol, current_price, quantity)
                                
                                # Only after the check completes successfully, reset the pending_check flag
                                if trade_executed or not ((not in_position and current_price <= buy_threshold) or \
                                                       (in_position and current_price >= sell_threshold)):
                                    self.pending_check = False
                                    print("Pending check flag reset after successful trade check")
                                else:
                                    print("Keeping pending check flag for next iteration since conditions still met but no trade executed")
                            else:
                                # Normal time-based check
                                trade_executed = self.check_and_execute_trades(symbol, current_price, quantity)
                                self.last_price_check = current_time
                            
                            # If this was a threshold-triggered check and no trade was executed,
                            # log additional information for debugging
                            if check_due_to_threshold_update:
                                with self.state_lock:
                                    in_position = self.in_position
                                
                                print(f"Threshold-triggered check result:")
                                print(f"  Trade executed: {trade_executed}")
                                print(f"  Current position: {'In position' if in_position else 'Not in position'}")
                                if not trade_executed:
                                    if not in_position:
                                        if current_price <= buy_threshold:
                                            print(f"  ALERT: Price ${current_price:.2f} is <= buy threshold ${buy_threshold:.2f} but no buy executed!")
                                        else:
                                            print(f"  No buy executed because price ${current_price:.2f} is > buy threshold ${buy_threshold:.2f}")
                                    else:
                                        if current_price >= sell_threshold:
                                            print(f"  ALERT: Price ${current_price:.2f} is >= sell threshold ${sell_threshold:.2f} but no sell executed!")
                                        else:
                                            print(f"  No sell executed because price ${current_price:.2f} is < sell threshold ${sell_threshold:.2f}")
                        except Exception as e:
                            print(f"Error during trade check: {str(e)}")
                            import traceback
                            traceback.print_exc()
                            
                            # If this was a threshold-triggered check and it failed, schedule another immediate check
                            if check_due_to_threshold_update:
                                print("Threshold-triggered check failed. Scheduling another immediate check.")
                                self.pending_check = True  # Keep the immediate check flag for next iteration
                    
                    # Update display
                    self.update_display(symbol, current_price, buy_threshold, sell_threshold)
                
                except Exception as e:
                    print(f"Error in trading loop iteration: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    consecutive_errors += 1
                    
                    # If we have too many consecutive errors, try to restart price fetching
                    if consecutive_errors > 5:
                        print("Too many consecutive errors. Restarting price fetching...")
                        self.data_fetcher.stop_price_fetching()
                        time.sleep(1)
                        self.data_fetcher.start_price_fetching(symbol)
                        consecutive_errors = 0
                
                # Use a shorter sleep interval if pending_check is set (waiting for a possible trade)
                if self.pending_check:
                    time.sleep(max(0.1, config.PRICE_CHECK_INTERVAL / 5))  # Much faster checks when trade is pending
                else:
                    # Wait for next iteration at normal speed
                    time.sleep(config.PRICE_CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            print("\nTrading bot stopped by user.")
            self.running = False
            self.data_fetcher.stop_price_fetching()
        except Exception as e:
            print(f"\nError in trading loop: {str(e)}")
            import traceback
            traceback.print_exc()
            self.running = False
            self.data_fetcher.stop_price_fetching()
    
    def _execute_buy(self, symbol, quantity, price, reason="OG_buy_sell_threshold_algo buy trigger"):
        """Execute a buy order and handle all related updates"""
        print(f"Executing BUY: {quantity} {symbol} at ${price:.2f} - Reason: {reason}")
        
        if not self.data_fetcher:
            print("ERROR: Cannot execute buy order - data_fetcher is not initialized")
            return False
            
        if quantity <= 0:
            print(f"ERROR: Invalid quantity for buy order: {quantity}")
            return False
            
        try:
            order = self.data_fetcher.place_buy_order(symbol, quantity)
            
            if order and order.get("status") == "filled":
                # Use state_lock to safely update the position state
                with self.state_lock:
                    self.in_position = True  # Update position status
                    self.last_action = f"Bought {quantity} {symbol} at ${price:.2f}"
                
                # Chart updates don't need to be inside the lock
                if self.chart_manager:
                    self.chart_manager.add_buy_trade(price, quantity, threshold_triggered=True)
                
                print(f"*** BUY ORDER SUCCESSFUL at ${price:.2f} ***")
                print(f"Position status updated to IN POSITION")
                return True
            else:
                error_msg = order.get("message", "Unknown error") if order else "No response from data_fetcher"
                print(f"!!! BUY ORDER FAILED: {error_msg}")
                print(f"Position status remains NOT IN POSITION")
                return False
        except Exception as e:
            print(f"!!! BUY ORDER FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"Position status remains NOT IN POSITION")
            return False
            
    def _execute_sell(self, symbol, quantity, price, reason="OG_buy_sell_threshold_algo sell trigger"):
        """Execute a sell order and handle all related updates"""
        print(f"Executing SELL: {quantity} {symbol} at ${price:.2f} - Reason: {reason}")
        
        if not self.data_fetcher:
            print("ERROR: Cannot execute sell order - data_fetcher is not initialized")
            return False
            
        if quantity <= 0:
            print(f"ERROR: Invalid quantity for sell order: {quantity}")
            return False
            
        try:
            order = self.data_fetcher.place_sell_order(symbol, quantity)
            
            if order and order.get("status") == "filled":
                # Use state_lock to safely update the position state
                with self.state_lock:
                    self.in_position = False  # Update position status
                    self.last_action = f"Sold {quantity} {symbol} at ${price:.2f}"
                
                # Chart updates don't need to be inside the lock
                if self.chart_manager:
                    self.chart_manager.add_sell_trade(price, quantity, threshold_triggered=True)
                
                print(f"*** SELL ORDER SUCCESSFUL at ${price:.2f} ***")
                print(f"Position status updated to NOT IN POSITION")
                return True
            else:
                error_msg = order.get("message", "Unknown error") if order else "No response from data_fetcher"
                print(f"!!! SELL ORDER FAILED: {error_msg}")
                print(f"Position status remains IN POSITION")
                return False
        except Exception as e:
            print(f"!!! SELL ORDER FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"Position status remains IN POSITION")
            return False
            
    def stop_trading(self):
        """Stop the trading loop"""
        self.running = False
        self.data_fetcher.stop_price_fetching() 