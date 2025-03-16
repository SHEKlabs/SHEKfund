from binance.client import Client
import time
import threading
import config

class DataFetcher:
    """Class to handle fetching data from Binance API"""
    
    def __init__(self, quiet_init=False):
        """Initialize with Binance client"""
        self.client = Client(config.API_KEY, config.API_SECRET_KEY, testnet=config.USE_TESTNET)
        self.latest_price = None
        self.last_updated = None
        self.current_symbol = None
        self.fetching_thread = None
        self.should_fetch = False
        self.quiet_init = quiet_init
        self.price_fetch_lock = threading.Lock()
        self.fetch_errors = 0  # Track consecutive fetch errors
        
        # Don't verify connection immediately if quiet_init is True
        if not quiet_init:
            self.verify_connection()
        
    def verify_connection(self):
        """Verify that we can connect to the Binance API"""
        try:
            self.client.get_account()
            if not self.quiet_init:
                print("Connected to Binance API successfully")
            return True
        except Exception as e:
            if not self.quiet_init:
                print(f"Error connecting to Binance API: {e}")
            return False

    def set_coin(self, symbol):
        """
        Update the coin/symbol to track prices for.
        
        Args:
            symbol (str): The trading pair symbol (e.g., 'BTCUSDT')
        """
        with self.price_fetch_lock:
            # Stop any existing fetching
            self.stop_price_fetching()
            
            # Update symbol and clear existing price data
            self.current_symbol = symbol
            self.latest_price = None
            self.last_updated = None
            self.fetch_errors = 0
            
            print(f"Coin set to {symbol}, cleared previous price data")
            
            # Start fetching for the new symbol
            self.start_price_fetching(symbol)

    def get_current_price(self, symbol=None, force_fresh=False):
        """
        Get the current price for a specific trading pair or the currently tracked symbol.
        
        Args:
            symbol (str, optional): The trading pair symbol. If None, uses current_symbol.
            force_fresh (bool): If True, always fetch a new price instead of using cached value
            
        Returns:
            float: The current price or None if unavailable
            
        Raises:
            ValueError: If no symbol is provided and no current_symbol is set
        """
        # If no symbol provided, use the current tracked symbol
        if symbol is None:
            if self.current_symbol is None:
                raise ValueError("No coin selected. Please select a coin first.")
            symbol = self.current_symbol
            
        # If we already have a latest price for the current symbol and not forcing fresh, return it
        if not force_fresh and symbol == self.current_symbol and self.latest_price is not None:
            print(f"Using cached price for {symbol}: ${self.latest_price:.2f}")
            return self.latest_price
            
        # Fetch a new price
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            
            # Update latest price data if this is for the current symbol
            if symbol == self.current_symbol:
                with self.price_fetch_lock:
                    self.latest_price = price
                    self.last_updated = time.strftime("%H:%M:%S", time.localtime())
                    self.fetch_errors = 0  # Reset error counter on successful fetch
            
            print(f"Fetched fresh price for {symbol}: ${price:.2f}")
            return price
        except Exception as e:
            self.fetch_errors += 1
            error_msg = f"Error fetching price for {symbol}: {e}"
            if not self.quiet_init or self.fetch_errors > 3:
                print(error_msg)
            return None
    
    def start_price_fetching(self, symbol):
        """Start fetching prices in a background thread"""
        # Set the current symbol
        self.current_symbol = symbol
        
        # Stop any existing fetching
        if self.fetching_thread and self.fetching_thread.is_alive():
            self.should_fetch = False
            self.fetching_thread.join(timeout=2.0)
            
        # Start new fetching thread
        self.should_fetch = True
        self.fetching_thread = threading.Thread(target=self._fetch_loop)
        self.fetching_thread.daemon = True
        self.fetching_thread.start()
        
        print(f"Started price fetching for {symbol}")
    
    def stop_price_fetching(self):
        """Stop the price fetching background thread"""
        if self.fetching_thread and self.fetching_thread.is_alive():
            self.should_fetch = False
            if not self.quiet_init:
                print("Stopped price fetching")
    
    def _fetch_loop(self):
        """Background thread function to continuously fetch prices"""
        while self.should_fetch and self.current_symbol:
            try:
                # Always force fresh price in the fetch loop
                price = self.get_current_price(self.current_symbol, force_fresh=True)
                if price is not None:
                    with self.price_fetch_lock:
                        self.latest_price = price
                        # Use a more detailed timestamp format
                        self.last_updated = time.strftime("%H:%M:%S", time.localtime())
                        
                        # Print detailed price information for trading decisions
                        print(f"[{self.last_updated}] Price updated for {self.current_symbol}: ${price:.2f}")
                else:
                    print(f"Price fetch failed for {self.current_symbol}, retrying...")
                    self.fetch_errors += 1
            except Exception as e:
                self.fetch_errors += 1
                print(f"Fetch loop error: {e}")
            
            # Sleep to avoid hammering the API, but use a shorter interval for more responsive trading
            time.sleep(0.5)  # Faster polling for real-time updates
    
    def get_latest_data(self):
        """Get the latest price data as a dictionary"""
        with self.price_fetch_lock:
            # Always update the timestamp to the current time if we have a price
            current_time = time.strftime("%H:%M:%S", time.localtime())
            
            return {
                "price": self.latest_price,
                "last_updated": self.last_updated or current_time,
                "symbol": self.current_symbol,
                "timestamp": int(time.time() * 1000)  # Add millisecond timestamp for frontend
            }
    
    def place_buy_order(self, symbol, quantity):
        """
        Place a market buy order on Binance.
        
        In a real implementation, this would place an actual order.
        For testing purposes, it just simulates a successful order.
        """
        print(f"SIMULATION: Placing buy order for {quantity} {symbol} at market price")
        
        # Validate inputs
        if not symbol or not isinstance(symbol, str):
            error_msg = f"Invalid symbol: {symbol}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "message": error_msg}
            
        if not quantity or quantity <= 0:
            error_msg = f"Invalid quantity: {quantity}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "message": error_msg}
        
        # Get the current price for the order - ALWAYS force fresh for orders
        try:
            current_price = self.get_current_price(symbol, force_fresh=True)
            if current_price is None:
                error_msg = "Could not get current price for buy order"
                print(f"ERROR: {error_msg}")
                return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Error fetching price for buy order: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "message": error_msg}
            
        # In a real implementation, this would call self.client.create_order()
        try:
            # For simulation, just return a successful response
            order_result = {
                "status": "filled",
                "orderId": int(time.time() * 1000),  # Unique ID based on timestamp
                "symbol": symbol,
                "price": current_price,
                "quantity": quantity,
                "side": "BUY",
                "type": "MARKET",
                "time": int(time.time() * 1000)
            }
            
            print(f"SIMULATION: Buy order filled at price ${current_price:.2f}")
            
            # Update the latest price to match what we just traded at
            with self.price_fetch_lock:
                self.latest_price = current_price
                self.last_updated = time.strftime("%H:%M:%S", time.localtime())
            
            return order_result
        except Exception as e:
            error_msg = f"Error executing buy order: {str(e)}"
            print(f"ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": error_msg}
    
    def place_sell_order(self, symbol, quantity):
        """
        Place a market sell order on Binance.
        
        In a real implementation, this would place an actual order.
        For testing purposes, it just simulates a successful order.
        """
        print(f"SIMULATION: Placing sell order for {quantity} {symbol} at market price")
        
        # Validate inputs
        if not symbol or not isinstance(symbol, str):
            error_msg = f"Invalid symbol: {symbol}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "message": error_msg}
            
        if not quantity or quantity <= 0:
            error_msg = f"Invalid quantity: {quantity}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "message": error_msg}
        
        # Get the current price for the order - ALWAYS force fresh for orders
        try:
            current_price = self.get_current_price(symbol, force_fresh=True)
            if current_price is None:
                error_msg = "Could not get current price for sell order"
                print(f"ERROR: {error_msg}")
                return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Error fetching price for sell order: {str(e)}"
            print(f"ERROR: {error_msg}")
            return {"status": "error", "message": error_msg}
            
        # In a real implementation, this would call self.client.create_order()
        try:
            # For simulation, just return a successful response
            order_result = {
                "status": "filled",
                "orderId": int(time.time() * 1000),  # Unique ID based on timestamp
                "symbol": symbol,
                "price": current_price,
                "quantity": quantity,
                "side": "SELL",
                "type": "MARKET",
                "time": int(time.time() * 1000)
            }
            
            print(f"SIMULATION: Sell order filled at price ${current_price:.2f}")
            
            # Update the latest price to match what we just traded at
            with self.price_fetch_lock:
                self.latest_price = current_price
                self.last_updated = time.strftime("%H:%M:%S", time.localtime())
            
            return order_result
        except Exception as e:
            error_msg = f"Error executing sell order: {str(e)}"
            print(f"ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": error_msg} 