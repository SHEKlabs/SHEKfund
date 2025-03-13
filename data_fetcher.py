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

    def get_current_price(self, symbol):
        """Get the current price for a specific trading pair"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            # Update latest price data
            self.latest_price = price
            self.last_updated = time.strftime("%H:%M:%S")
            return price
        except Exception as e:
            if not self.quiet_init:
                print(f"Error fetching price for {symbol}: {e}")
            return None
    
    def start_price_fetching(self, symbol):
        """Start fetching prices in a background thread"""
        self.current_symbol = symbol
        self.should_fetch = True
        
        if self.fetching_thread and self.fetching_thread.is_alive():
            if not self.quiet_init:
                print("Price fetching thread already running")
            return
            
        self.fetching_thread = threading.Thread(target=self._fetch_loop)
        self.fetching_thread.daemon = True
        self.fetching_thread.start()
        if not self.quiet_init:
            print(f"Started price fetching for {symbol}")
        
    def stop_price_fetching(self):
        """Stop the price fetching thread"""
        self.should_fetch = False
        if self.fetching_thread:
            # The thread will terminate on next iteration due to should_fetch=False
            if not self.quiet_init:
                print("Stopping price fetching...")
    
    def _fetch_loop(self):
        """Background loop to continuously fetch prices"""
        while self.should_fetch and self.current_symbol:
            price = self.get_current_price(self.current_symbol)
            if price:
                if not self.quiet_init:
                    print(f"Fetched price for {self.current_symbol}: ${price:.2f} at {self.last_updated}")
            else:
                if not self.quiet_init:
                    print(f"Failed to fetch price for {self.current_symbol}")
                
            # Wait for specified interval before fetching again
            time.sleep(config.PRICE_CHECK_INTERVAL)
    
    def get_latest_data(self):
        """Return the latest price data"""
        return {
            "symbol": self.current_symbol,
            "price": self.latest_price,
            "last_updated": self.last_updated
        }
            
    def place_buy_order(self, symbol, quantity):
        """Place a market buy order"""
        try:
            order = self.client.order_market_buy(symbol=symbol, quantity=quantity)
            print(f"Buy Order Done: {order}")
            return order
        except Exception as e:
            print(f"Error placing buy order: {e}")
            return None
            
    def place_sell_order(self, symbol, quantity):
        """Place a market sell order"""
        try:
            order = self.client.order_market_sell(symbol=symbol, quantity=quantity)
            print(f"Sell Order Done: {order}")
            return order
        except Exception as e:
            print(f"Error placing sell order: {e}")
            return None 