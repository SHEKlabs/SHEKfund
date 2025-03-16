#Youtube tutorial Link: https://www.youtube.com/watch?v=K15KVuNvk9s 

import time
import os
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
from algo_library import ALGO_LIBRARY

def print_welcome():
    """Print welcome message to console"""
    print("~~~~ Welcome to SHEKfund Trading Bot ~~~~")
    print("Access the trading dashboard at: http://localhost:%s" % config.PORT)
    print("------------------------------------------")
    print("IMPORTANT: For proper trading with OG_buy_sell_threshold_algo:")
    print("1. Select a coin and the OG algorithm")
    print("2. Set your Buy and Sell thresholds")
    print("3. Click 'Start Trading' to begin")
    print("4. Trades will execute when price crosses thresholds")
    print("------------------------------------------")

def main():
    """Main entry point of the application with web-based interaction"""
    print_welcome()
    
    # Initialize components with default values
    data_fetcher = DataFetcher(quiet_init=True)
    chart_manager = ChartManager()
    
    # Create default algorithm - will be properly initialized via web UI
    default_algo_name = "OG_buy_sell_threshold_algo"
    
    print("\nInitializing default algorithm:", default_algo_name)
    algorithm_instance = ALGO_LIBRARY[default_algo_name]()
    
    # For OG algo, make sure it's properly initialized with default thresholds
    # These will be replaced when the user sets thresholds
    if hasattr(algorithm_instance, 'set_thresholds'):
        # Use default thresholds from first available coin 
        # (will be overridden by user selection later)
        first_coin = next(iter(COIN_CONFIGS.values()), {})
        buy_threshold = first_coin.get('buy_threshold', 0)
        sell_threshold = first_coin.get('sell_threshold', 0)
        algorithm_instance.set_thresholds(buy_threshold, sell_threshold)
        print(f"Default thresholds set: Buy=${buy_threshold}, Sell=${sell_threshold}")
    
    # Initialize trading bot with the default algorithm
    # The actual trading will only start when user selects options in the web UI
    trading_bot = TradingBot(data_fetcher, chart_manager, algorithm_instance, default_algo_name)
    
    # Initialize web server
    web_server = WebServer(trading_bot, data_fetcher, default_algo_name)
    
    # Start web server first
    print("\nStarting web server...")
    web_server.start()
    
    # Tell user how to access the web interface
    print("\n************************************************************")
    print("✅ Web server started successfully!")
    print(f"✅ Please open the web interface in your browser at:")
    print(f"   http://localhost:{config.PORT}")
    print("\n✅ To properly use the trading system:")
    print("   1. Select a coin from the dropdown")
    print("   2. Select the OG_buy_sell_threshold_algo algorithm")
    print("   3. Set your buy and sell thresholds (percentage or absolute price)")
    print("   4. Click 'Start Trading' to begin - trades will execute automatically")
    print("************************************************************\n")

    # Keep the main thread running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down SHEKfund Trading Bot...")
        # Stop the trading bot first
        if hasattr(trading_bot, 'stop_trading'):
            trading_bot.stop_trading()
            
        # Shutdown the web server using the new method
        if hasattr(web_server, 'shutdown'):
            web_server.shutdown()
        else:
            # Clean way to shut down Flask - add this
            print("Shutting down web server...")
            try:
                # Force close any socket connections
                import socket
                from werkzeug.serving import make_server
                # Try to release the port by creating a server and closing it
                temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                temp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    temp_socket.bind((config.HOST, config.PORT))
                except:
                    pass
                finally:
                    temp_socket.close()
            except Exception as e:
                print(f"Error during port cleanup: {e}")
            
        print("Bot stopped. Thank you for using SHEKfund Trading Bot!")

if __name__ == "__main__":
    main()