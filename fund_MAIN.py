#Youtube tutorial Link: https://www.youtube.com/watch?v=K15KVuNvk9s 

import time
import os
import sys
import logging
import threading
from datetime import datetime
from binance.client import Client 
from flask import Flask, jsonify, render_template

# Import our configuration files
import config
from coin_configs import AVAILABLE_COINS, COIN_CONFIGS
from data_fetcher import DataFetcher
from chart_manager import ChartManager
from trading_bot import TradingBot
from web_server import WebServer

def print_welcome():
    """Print welcome message"""
    print("~~~~ Welcome to the Main script of the shekFUND ~~~~")
    print("... I just pushed this code to my git repo: https://github.com/SHEKlabs/SHEKfund ...")

def display_available_coins():
    """Display available coins for selection"""
    print("\nAvailable coins:")
    for i, coin in enumerate(AVAILABLE_COINS, 1):
        print(f"{i}. {coin}")

def get_user_selection():
    """Get user selection of coin to trade"""
    selection = input("--> Enter the number of the coin you want to trade with: ")
    
    try:
        index = int(selection) - 1
        if 0 <= index < len(AVAILABLE_COINS):
            selected_coin = AVAILABLE_COINS[index]
            coin_config = COIN_CONFIGS[selected_coin]
            return selected_coin, coin_config
        else:
            print("Invalid selection. Please run the script again and select a valid option.")
            return None, None
    except ValueError:
        print("Please enter a valid number. Run the script again to try again.")
        return None, None

def main():
    """Main entry point of the application"""
    print_welcome()
    
    # Initialize components with quiet initialization
    data_fetcher = DataFetcher(quiet_init=True)
    chart_manager = ChartManager()
    trading_bot = TradingBot(data_fetcher, chart_manager)
    
    # Configure web server
    web_server = WebServer(chart_manager, data_fetcher)
    
    # Start web server first
    print("Starting web server...")
    web_server.start()
    
    # Tell user how to access the web interface with clear instruction
    print("\n************************************************************")
    print("✅ Web server started successfully!")
    print(f"✅ Please open the web interface in your browser at:")
    print(f"   http://localhost:{config.PORT}")
    print("************************************************************\n")
    
    # Now get coin selection from user
    display_available_coins()
    selected_coin, coin_config = get_user_selection()
    if selected_coin is None or coin_config is None:
        return
    
    print(f"\nSelected {selected_coin} for trading.")
    print(f"Configuration: Buy Threshold: ${coin_config['buy_threshold']}, "
          f"Sell Threshold: ${coin_config['sell_threshold']}, "
          f"Quantity: {coin_config['quantity']}")
    
    # Update chart_manager with selected coin and thresholds
    chart_manager.set_symbol_and_thresholds(
        selected_coin, 
        coin_config['buy_threshold'], 
        coin_config['sell_threshold']
    )
    
    # Wait for user confirmation
    start = input("--> Press Enter to start trading, or type 'quit' to exit: ")
    if start.lower() == 'quit':
        print("Exiting application.")
        return
    
    # Verify connectivity before starting
    print("Verifying connection to Binance API...")
    if not data_fetcher.verify_connection():
        print("Failed to connect to Binance API. Please check your internet connection and API keys.")
        return
    
    print("\n************************************************************")
    print("✅ Trading bot has started!")
    print("✅ The chart should now be updating in your browser.")
    print("✅ Press Ctrl+C to stop the trading bot.")
    print("************************************************************\n")
    
    # Start trading bot
    trading_bot.start_trading(
        selected_coin, 
        coin_config['buy_threshold'], 
        coin_config['sell_threshold'], 
        coin_config['quantity']
    )

if __name__ == "__main__":
    main()