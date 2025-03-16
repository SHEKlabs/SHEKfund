from flask import Flask, jsonify, render_template, request
import threading
import config
import logging
import sys
from coin_configs import AVAILABLE_COINS
from algo_library import ALGO_LIBRARY
import time

class WebServer:
    """Class to handle the web server functionality"""
    
    def __init__(self, trading_bot, data_fetcher=None, algorithm_name="OG_buy_sell_threshold_algo"):
        """Initialize with dependencies"""
        self.trading_bot = trading_bot
        self.data_fetcher = data_fetcher
        self.algorithm_name = algorithm_name
        
        # Configure logging based on configuration
        if config.FLASK_QUIET:
            # Set Flask's logger to only show errors
            log = logging.getLogger('werkzeug')
            log.setLevel(getattr(logging, config.FLASK_LOG_LEVEL))
            
            # Redirect Flask output to avoid cluttering the terminal
            if config.FLASK_LOG_LEVEL == 'ERROR':
                log.disabled = True
        
        # Initialize Flask app with minimal logging
        self.app = Flask(__name__)
        self.app.logger.setLevel(getattr(logging, config.FLASK_LOG_LEVEL))
        self.setup_routes()
        
    def setup_routes(self):
        """Set up the Flask routes"""
        # Create local references to use in route functions
        trading_bot = self.trading_bot
        data_fetcher = self.data_fetcher
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/available_coins')
        def get_available_coins():
            """Return list of available coins for selection"""
            return jsonify({"status": "success", "coins": AVAILABLE_COINS})
        
        @self.app.route('/available_algorithms')
        def get_available_algorithms():
            """Return list of available trading algorithms"""
            return jsonify({"status": "success", "algorithms": list(ALGO_LIBRARY.keys())})
        
        @self.app.route('/select_coin', methods=['POST'])
        def select_coin():
            """Handle coin selection"""
            try:
                data = request.json
                coin = data.get('coin')
                
                if coin not in AVAILABLE_COINS:
                    return jsonify({
                        "status": "error", 
                        "message": f"Invalid coin selected: {coin}"
                    })
                
                # Update the data fetcher to track the selected coin
                if data_fetcher:
                    data_fetcher.set_coin(coin)
                    
                return jsonify({
                    "status": "success", 
                    "message": f"Selected coin: {coin}"
                })
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)})
        
        @self.app.route('/select_algorithm', methods=['POST'])
        def select_algorithm():
            """Handle algorithm selection"""
            try:
                data = request.json
                algorithm = data.get('algorithm')
                
                if algorithm not in ALGO_LIBRARY:
                    return jsonify({
                        "status": "error", 
                        "message": f"Invalid algorithm selected: {algorithm}"
                    })
                
                # Create a new instance of the selected algorithm
                algo_instance = ALGO_LIBRARY[algorithm]()
                
                # Update the trading bot with the new algorithm
                trading_bot.algorithm = algo_instance
                trading_bot.algorithm_name = algorithm
                
                return jsonify({
                    "status": "success", 
                    "message": f"Selected algorithm: {algorithm}"
                })
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)})
        
        @self.app.route('/current_price')
        def get_current_price():
            """Get the current price of the selected coin"""
            try:
                if data_fetcher:
                    # Force a fresh price fetch rather than using a potentially cached value
                    if data_fetcher.current_symbol:
                        current_price = data_fetcher.get_current_price(data_fetcher.current_symbol)
                        print(f"Fetched fresh price for {data_fetcher.current_symbol}: {current_price}")
                    else:
                        # No coin selected yet
                        current_price = None
                        print("No coin selected yet, can't fetch price")
                    
                    return jsonify({
                        "status": "success", 
                        "price": current_price,
                        "timestamp": int(time.time() * 1000)  # Include timestamp for freshness verification
                    })
                else:
                    return jsonify({
                        "status": "error", 
                        "message": "Data fetcher not available"
                    })
            except Exception as e:
                print(f"Error in current_price endpoint: {str(e)}")
                return jsonify({"status": "error", "message": str(e)})
        
        @self.app.route('/start_trading', methods=['POST'])
        def start_trading():
            """Start trading with the selected coin and algorithm"""
            try:
                data = request.json
                coin = data.get('coin')
                algorithm = data.get('algorithm')
                
                if coin not in AVAILABLE_COINS:
                    return jsonify({
                        "status": "error", 
                        "message": f"Invalid coin selected: {coin}"
                    })
                
                if algorithm not in ALGO_LIBRARY:
                    return jsonify({
                        "status": "error", 
                        "message": f"Invalid algorithm selected: {algorithm}"
                    })
                
                # Get coin configuration
                from coin_configs import COIN_CONFIGS
                coin_config = COIN_CONFIGS.get(coin, {})
                
                if not coin_config:
                    return jsonify({
                        "status": "error",
                        "message": f"No configuration found for {coin}"
                    })
                
                # Get current thresholds if they were set by the user
                current_thresholds = trading_bot.get_current_thresholds()
                buy_threshold = current_thresholds.get('buy')
                sell_threshold = current_thresholds.get('sell')
                
                # If no thresholds were set by the user, use the coin config defaults
                if buy_threshold is None or sell_threshold is None:
                    buy_threshold = coin_config.get('buy_threshold', 0)
                    sell_threshold = coin_config.get('sell_threshold', 0)
                    
                # Get quantity from coin config
                quantity = coin_config.get('quantity', 0)
                
                # Make sure data_fetcher knows which coin we're trading
                if data_fetcher:
                    data_fetcher.set_coin(coin)
                    
                # Create and set the algorithm
                algo_instance = ALGO_LIBRARY[algorithm]()
                trading_bot.algorithm = algo_instance
                trading_bot.algorithm_name = algorithm
                
                # Clear any previous trading state
                trading_bot.stop_trading()
                
                # Log the actual values for debugging
                print(f"Starting trading with: Coin={coin}, Algorithm={algorithm}, Buy threshold=${buy_threshold}, Sell threshold=${sell_threshold}, Quantity={quantity}")
                
                # Start trading in a separate thread to not block the web request
                trading_thread = threading.Thread(
                    target=trading_bot.start_trading,
                    args=(coin, buy_threshold, sell_threshold, quantity)
                )
                trading_thread.daemon = True
                trading_thread.start()
                
                return jsonify({
                    "status": "success", 
                    "message": f"Trading started with {coin} using {algorithm} algorithm",
                    "thresholds": {
                        "buy": buy_threshold,
                        "sell": sell_threshold
                    }
                })
                
            except Exception as e:
                print(f"Error in start_trading: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({"status": "error", "message": str(e)})
            
        @self.app.route('/data')
        def get_data():
            chart_data = trading_bot.chart_manager.get_chart_data()
            # Add algorithm name to the data
            chart_data["algorithm_name"] = trading_bot.get_algorithm_name()
            return jsonify(chart_data)
        
        @self.app.route('/update')
        def get_update():
            """Endpoint for real-time price updates"""
            try:
                if data_fetcher:
                    # Get data with a timeout to prevent hanging
                    start_time = time.time()
                    latest_data = data_fetcher.get_latest_data()
                    chart_data = trading_bot.chart_manager.get_chart_data()
                    
                    # Make sure trade_log is properly included and renamed to 'trades' for frontend compatibility
                    if 'trade_log' in chart_data:
                        chart_data['trades'] = chart_data['trade_log']
                    
                    # Combine data with algorithm name
                    response = {
                        "price": latest_data.get("price"),
                        "symbol": latest_data.get("symbol"),
                        "last_updated": latest_data.get("last_updated"),
                        "chart_data": chart_data,
                        "algorithm_name": trading_bot.get_algorithm_name(),
                        "response_time_ms": int((time.time() - start_time) * 1000)  # Track response time for debugging
                    }
                    
                    # Ensure response contains good Last Updated information
                    if not response.get("last_updated"):
                        response["last_updated"] = time.strftime("%H:%M:%S", time.localtime())
                        
                    return jsonify(response)
                else:
                    return jsonify({
                        "error": "Data fetcher not available",
                        "timestamp": int(time.time() * 1000)
                    }), 503
            except Exception as e:
                print(f"Error in update endpoint: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    "error": f"Error fetching update: {str(e)}",
                    "timestamp": int(time.time() * 1000)
                }), 500
        
        @self.app.route('/update_thresholds', methods=['POST'])
        def update_thresholds():
            """
            Handle threshold update requests from the web interface.
            Supports both percentage-based and fixed price threshold updates.
            """
            try:
                data = request.json
                threshold_type = data.get('type', 'price')  # 'percentage' or 'price'
                buy_value = float(data.get('buy_value', 0))
                sell_value = float(data.get('sell_value', 0))
                
                print(f"\n======== THRESHOLD UPDATE REQUEST =========")
                print(f"Type: {threshold_type}, Buy value: {buy_value}, Sell value: {sell_value}")
                
                # Check if selected algorithm supports thresholds
                if trading_bot.algorithm_name != "OG_buy_sell_threshold_algo":
                    print(f"Algorithm {trading_bot.algorithm_name} does not support threshold settings")
                    return jsonify({
                        "status": "error",
                        "message": f"Algorithm {trading_bot.algorithm_name} does not support threshold settings"
                    })
                
                # Get current price for percentage calculations
                if threshold_type == 'percentage' and data_fetcher:
                    try:
                        # Force fresh price fetch with the current symbol
                        if data_fetcher.current_symbol:
                            current_price = data_fetcher.get_current_price(data_fetcher.current_symbol, force_fresh=True)
                            
                            if current_price is None:
                                error_msg = "Current price not available for percentage calculation. Try again when price data is available."
                                print(error_msg)
                                return jsonify({
                                    "status": "error", 
                                    "message": error_msg
                                })
                            
                            # Convert percentages to absolute prices
                            # Buy is typically a negative percentage (below current price)
                            # Sell is typically a positive percentage (above current price)
                            buy_threshold = current_price * (1 + buy_value / 100)
                            sell_threshold = current_price * (1 + sell_value / 100)
                            
                            print(f"Calculated thresholds from percentages - Current price: ${current_price}, Buy: ${buy_threshold} ({buy_value}%), Sell: ${sell_threshold} ({sell_value}%)")
                        else:
                            print("No coin selected for percentage calculation")
                            return jsonify({
                                "status": "error", 
                                "message": "No coin selected. Please select a coin first."
                            })
                    except Exception as e:
                        print(f"Price calculation error: {str(e)}")
                        return jsonify({
                            "status": "error", 
                            "message": f"Price calculation error: {str(e)}"
                        })
                else:
                    # Use direct price values
                    buy_threshold = buy_value
                    sell_threshold = sell_value
                    print(f"Using direct price thresholds - Buy: ${buy_threshold}, Sell: ${sell_threshold}")
                
                # Verify the thresholds make sense (buy < sell)
                if buy_threshold >= sell_threshold:
                    print(f"WARNING: Buy threshold (${buy_threshold}) >= Sell threshold (${sell_threshold}). This may cause unexpected behavior.")
                
                # Update the trading bot's thresholds
                print(f"Applying thresholds to trading bot - Buy: ${buy_threshold}, Sell: ${sell_threshold}")
                
                # Store the old thresholds for comparison
                old_thresholds = trading_bot.get_current_thresholds()
                
                # Update the thresholds in the trading bot - THIS IS THE CRITICAL PART
                trading_bot.update_thresholds(buy_threshold, sell_threshold)
                
                # Force the trading bot to check for trades immediately
                if data_fetcher and data_fetcher.current_symbol and trading_bot.running:
                    current_price = data_fetcher.get_current_price(data_fetcher.current_symbol, force_fresh=True)
                    if current_price is not None:
                        # Force an immediate trade check with the new thresholds
                        print(f"Forcing immediate trade check with new thresholds and current price: ${current_price}")
                        
                        # Get coin configuration for quantity
                        from coin_configs import COIN_CONFIGS
                        coin_config = COIN_CONFIGS.get(data_fetcher.current_symbol, {})
                        quantity = coin_config.get('quantity', 0.001)  # Default quantity if not found
                        
                        # Execute the trade check directly
                        trading_bot.check_and_execute_trades(data_fetcher.current_symbol, current_price, quantity)
                
                # Verify the thresholds were set correctly
                current_thresholds = trading_bot.get_current_thresholds()
                print(f"Verified new thresholds - Buy: ${current_thresholds['buy']}, Sell: ${current_thresholds['sell']}")
                
                # If thresholds don't match what we set, there's a problem
                if (abs(current_thresholds['buy'] - buy_threshold) > 0.01 or 
                    abs(current_thresholds['sell'] - sell_threshold) > 0.01):
                    print(f"WARNING: Threshold mismatch! Set: ${buy_threshold}/{sell_threshold}, Got: ${current_thresholds['buy']}/${current_thresholds['sell']}")
                    return jsonify({
                        "status": "error", 
                        "message": f"Failed to update thresholds correctly. Please try again."
                    })
                
                # Force check for trades now that thresholds are updated
                if data_fetcher and data_fetcher.current_symbol:
                    current_price = data_fetcher.get_current_price(data_fetcher.current_symbol, force_fresh=True)
                    if current_price is not None:
                        print(f"Current price after threshold update: ${current_price}")
                        
                        # Display detailed information about the current state
                        price_vs_buy = "BELOW" if current_price <= current_thresholds['buy'] else "ABOVE"
                        price_vs_sell = "BELOW" if current_price <= current_thresholds['sell'] else "ABOVE"
                        in_position = trading_bot.in_position
                        
                        print(f"TRADE CHECK: Price ${current_price} is {price_vs_buy} buy threshold ${current_thresholds['buy']} and {price_vs_sell} sell threshold ${current_thresholds['sell']}")
                        print(f"POSITION STATE: {'In position' if in_position else 'Not in position'}")
                        
                        # Check for possible trades
                        if not in_position and current_price <= current_thresholds['buy']:
                            print(f"SIGNAL: Current price ${current_price} is BELOW buy threshold ${current_thresholds['buy']} - expect a BUY signal")
                        elif in_position and current_price >= current_thresholds['sell']:
                            print(f"SIGNAL: Current price ${current_price} is ABOVE sell threshold ${current_thresholds['sell']} - expect a SELL signal")
                        else:
                            print(f"SIGNAL: No trade signal generated for current conditions")
                        
                        # Notify the user about significant threshold changes that might affect trading
                        if old_thresholds['buy'] != current_thresholds['buy'] or old_thresholds['sell'] != current_thresholds['sell']:
                            print(f"NOTIFICATION: Thresholds changed significantly from Buy: ${old_thresholds['buy']}, Sell: ${old_thresholds['sell']} to Buy: ${current_thresholds['buy']}, Sell: ${current_thresholds['sell']}")
                
                print(f"======== THRESHOLD UPDATE COMPLETE =========\n")
                
                return jsonify({
                    "status": "success", 
                    "message": "Thresholds updated successfully",
                    "buy_threshold": current_thresholds['buy'],
                    "sell_threshold": current_thresholds['sell'],
                    "current_price": current_price if current_price is not None else 0
                })
            except Exception as e:
                print(f"Error updating thresholds: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({"status": "error", "message": str(e)})
            
    def start(self):
        """Start the Flask server in a thread"""
        # Determine whether to capture stdout from Flask
        if config.FLASK_QUIET:
            # Capture and discard stdout to prevent Flask startup messages
            original_stdout = sys.stdout
            sys.stdout = open('/dev/null', 'w')  # Redirect to /dev/null (Unix-like)
            
        try:
            self.server_thread = threading.Thread(
                target=lambda: self.app.run(
                    host=config.HOST, 
                    port=config.PORT, 
                    debug=config.DEBUG, 
                    use_reloader=config.USE_RELOADER
                )
            )
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # Only print the message - don't print Flask internal logs
            print(f"Web server started at http://{config.HOST}:{config.PORT}")
            return self.server_thread
            
        finally:
            # Restore stdout if we redirected it
            if config.FLASK_QUIET:
                sys.stdout.close()
                sys.stdout = original_stdout 