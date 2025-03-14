import time
import os
from datetime import datetime
import config

class TradingBot:
    """Class to handle trading logic and execution"""
    
    def __init__(self, data_fetcher, chart_manager):
        """Initialize with dependencies"""
        self.data_fetcher = data_fetcher
        self.chart_manager = chart_manager
        self.in_position = False
        self.last_action = "None"
        self.running = False
        
    def update_display(self, symbol, current_price, buy_threshold, sell_threshold):
        """Update the terminal display with current status"""
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear console
        print("~~~~ SHEKfund Trading Bot ~~~~")
        print(f"Selected Coin: {symbol}")
        print(f"Current Price: ${current_price:.2f}")
        print(f"Buy Threshold: ${buy_threshold:.2f}")
        print(f"Sell Threshold: ${sell_threshold:.2f}")
        print(f"Position Status: {'In Position' if self.in_position else 'Not In Position'}")
        print(f"Last Action: {self.last_action}")
        print(f"Web Interface: http://localhost:{config.PORT}")
        print("Press Ctrl+C to exit")
        print("----------------------------")
        now = datetime.now()
        formatted_date_time = now.strftime("< %d-%m-%Y | %H:%M:%S >")
        print(f"Last updated: {formatted_date_time}")
        
    def start_trading(self, symbol, buy_threshold, sell_threshold, quantity):
        """Start the trading loop for a specific coin"""
        # Set up initial state
        self.running = True
        self.in_position = False
        self.last_action = "None"
        
        # Configure chart manager
        self.chart_manager.set_symbol_and_thresholds(symbol, buy_threshold, sell_threshold)
        self.chart_manager.clear_data()
        
        # Start continuous price fetching
        self.data_fetcher.start_price_fetching(symbol)
        
        # Get initial price and update display
        current_price = self.data_fetcher.get_current_price(symbol)
        if current_price is None:
            print(f"Error: Could not fetch initial price for {symbol}")
            return
            
        # Add initial price point to chart
        self.chart_manager.add_price_point(current_price)
        
        # Initial display update
        self.update_display(symbol, current_price, buy_threshold, sell_threshold)
        
        # Main trading loop
        try:
            while self.running:
                latest_data = self.data_fetcher.get_latest_data()
                current_price = latest_data.get("price")
                
                if current_price is None:
                    print("No price data available. Waiting...")
                    time.sleep(config.PRICE_CHECK_INTERVAL)
                    continue
                
                # Record price point for chart
                self.chart_manager.add_price_point(current_price)
                
                # Trading logic
                if not self.in_position:
                    if current_price < buy_threshold:
                        print(f"Price is BELOW {buy_threshold}. Placing BUY order.")
                        order = self.data_fetcher.place_buy_order(symbol, quantity)
                        if order:
                            self.in_position = True
                            self.last_action = f"Bought at ${current_price:.2f}"
                            # Record detailed buy trade with threshold triggered flag
                            self.chart_manager.add_buy_trade(current_price, quantity, threshold_triggered=True)
                else:
                    if current_price > sell_threshold:
                        print(f"Price is ABOVE {sell_threshold}. Placing SELL order.")
                        order = self.data_fetcher.place_sell_order(symbol, quantity)
                        if order:
                            self.in_position = False
                            self.last_action = f"Sold at ${current_price:.2f}"
                            # Record detailed sell trade with threshold triggered flag
                            self.chart_manager.add_sell_trade(current_price, quantity, threshold_triggered=True)
                
                # Update display
                self.update_display(symbol, current_price, buy_threshold, sell_threshold)
                
                # Wait for next iteration
                time.sleep(config.PRICE_CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            print("\nTrading bot stopped by user.")
            self.running = False
            self.data_fetcher.stop_price_fetching()
            
    def stop_trading(self):
        """Stop the trading loop"""
        self.running = False
        self.data_fetcher.stop_price_fetching() 