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
        self.port = config.PORT  # Add port attribute
        
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
        
        @self.app.route('/shutdown', methods=['GET'])
        def shutdown_server():
            """Shutdown the Flask server (will only work in development mode)"""
            try:
                # Only works in werkzeug development server
                func = request.environ.get('werkzeug.server.shutdown')
                if func is None:
                    return jsonify({"status": "error", "message": "Not running in Werkzeug server"})
                func()
                return jsonify({"status": "success", "message": "Server shutting down..."})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)})
        
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
                    # Check if force_fresh is requested in the query parameters
                    force_fresh = 'force_fresh' in request.args
                    
                    # Force a fresh price fetch rather than using a potentially cached value
                    if data_fetcher.current_symbol:
                        current_price = data_fetcher.get_current_price(data_fetcher.current_symbol, force_fresh=force_fresh)
                        print(f"Fetched {'fresh' if force_fresh else 'cached'} price for {data_fetcher.current_symbol}: {current_price}")
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
                
                # Validate required inputs
                if not coin:
                    return jsonify({
                        "status": "error", 
                        "message": "No coin selected"
                    })
                    
                if not algorithm:
                    return jsonify({
                        "status": "error", 
                        "message": "No algorithm selected"
                    })
                
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
                buy_threshold = data.get('buy_threshold', current_thresholds.get('buy'))
                sell_threshold = data.get('sell_threshold', current_thresholds.get('sell'))
                
                # If no thresholds were set by the user, use the coin config defaults
                if buy_threshold is None or sell_threshold is None:
                    buy_threshold = coin_config.get('buy_threshold', 0)
                    sell_threshold = coin_config.get('sell_threshold', 0)
                    
                # Convert thresholds to float to ensure they're numeric
                try:
                    buy_threshold = float(buy_threshold)
                    sell_threshold = float(sell_threshold)
                except (ValueError, TypeError) as e:
                    return jsonify({
                        "status": "error",
                        "message": f"Invalid threshold values: buy={buy_threshold}, sell={sell_threshold}. Error: {str(e)}"
                    })
                
                # Validate thresholds
                if buy_threshold <= 0 or sell_threshold <= 0:
                    return jsonify({
                        "status": "error",
                        "message": f"Invalid threshold values: buy=${buy_threshold}, sell=${sell_threshold}. Thresholds must be positive."
                    })
                    
                if buy_threshold >= sell_threshold:
                    return jsonify({
                        "status": "warning",
                        "message": f"Buy threshold (${buy_threshold}) is greater than or equal to sell threshold (${sell_threshold}). Trading may not occur as expected."
                    })
                
                # Get quantity from coin config
                quantity = coin_config.get('quantity', 0)
                if quantity <= 0:
                    return jsonify({
                        "status": "error",
                        "message": f"Invalid quantity in coin config: {quantity}. Quantity must be positive."
                    })
                
                # Make sure data_fetcher knows which coin we're trading
                if data_fetcher:
                    try:
                        data_fetcher.set_coin(coin)
                    except Exception as e:
                        print(f"Error setting coin in data_fetcher: {str(e)}")
                        return jsonify({
                            "status": "error",
                            "message": f"Failed to initialize price fetching for {coin}: {str(e)}"
                        })
                else:
                    return jsonify({
                        "status": "error",
                        "message": "Data fetcher not initialized"
                    })
                    
                # Create and set the algorithm
                try:
                    algo_instance = ALGO_LIBRARY[algorithm]()
                    trading_bot.algorithm = algo_instance
                    trading_bot.algorithm_name = algorithm
                    
                    # Set the algorithm thresholds
                    if hasattr(algo_instance, 'set_thresholds') and callable(getattr(algo_instance, 'set_thresholds')):
                        algo_instance.set_thresholds(buy_threshold, sell_threshold)
                except Exception as e:
                    print(f"Error initializing algorithm: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({
                        "status": "error",
                        "message": f"Failed to initialize algorithm {algorithm}: {str(e)}"
                    })
                
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
            """Endpoint for real-time price updates with enhanced data"""
            try:
                if data_fetcher:
                    # Get data with a timeout to prevent hanging
                    start_time = time.time()
                    latest_data = data_fetcher.get_latest_data()
                    chart_data = trading_bot.chart_manager.get_chart_data()
                    current_thresholds = trading_bot.get_current_thresholds()
                    
                    # Thread-safe access to in_position state
                    with trading_bot.state_lock:
                        in_position = trading_bot.in_position
                    
                    # Make sure trade_log is properly included and renamed to 'trades' for frontend compatibility
                    if 'trade_log' in chart_data:
                        chart_data['trades'] = chart_data['trade_log']
                    
                    # Combine data with algorithm name and current thresholds
                    response = {
                        "price": latest_data.get("price"),
                        "symbol": latest_data.get("symbol"),
                        "last_updated": latest_data.get("last_updated"),
                        "chart_data": chart_data,
                        "algorithm_name": trading_bot.get_algorithm_name(),
                        "buy_threshold": current_thresholds['buy'],
                        "sell_threshold": current_thresholds['sell'],
                        "in_position": in_position,
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
                # The update_thresholds method will handle checking for trades with the new thresholds
                trading_bot.update_thresholds(buy_threshold, sell_threshold)
                
                # Note: We no longer need to force a trade check here as update_thresholds already does that
                # This eliminates the duplicate trade check and potential race condition
                
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
                        
                        # Get the position state in a thread-safe way
                        with trading_bot.state_lock:
                            in_position = trading_bot.in_position
                        
                        # Display detailed information about the current state
                        price_vs_buy = "BELOW" if current_price <= current_thresholds['buy'] else "ABOVE"
                        price_vs_sell = "BELOW" if current_price <= current_thresholds['sell'] else "ABOVE"
                        
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
            
        @self.app.route('/execute_buy', methods=['POST'])
        def execute_buy():
            """
            Execute a buy order from the web interface.
            
            POST parameters:
                amount: The amount to buy (either in USD or in coin units)
                amount_type: 'usd' or 'coin' to specify what the amount represents
            
            Returns:
                JSON response with order status
            """
            try:
                data = request.json
                amount = float(data.get('amount', 0))
                amount_type = data.get('amount_type', 'usd')  # Default to USD
                
                if amount <= 0:
                    return jsonify({
                        "status": "error",
                        "message": f"Invalid amount: {amount}"
                    })
                
                # Get latest price
                current_price = self.data_fetcher.get_current_price()
                if not current_price:
                    return jsonify({
                        "status": "error",
                        "message": "Could not get current price"
                    })
                
                # Calculate quantity based on amount type
                if amount_type == 'usd':
                    usd_amount = amount
                    coin_quantity = usd_amount / current_price
                else:  # amount_type == 'coin'
                    coin_quantity = amount
                    usd_amount = amount * current_price
                
                # Place the buy order
                order = self.data_fetcher.place_buy_order(self.data_fetcher.current_symbol, coin_quantity)
                
                if order and order.get("status") == "filled":
                    # Update trading bot's position status if it's tracking this coin
                    # Only check if symbols match, don't require the bot to be running
                    if hasattr(trading_bot, 'data_fetcher') and trading_bot.data_fetcher and trading_bot.data_fetcher.current_symbol == self.data_fetcher.current_symbol:
                        # Thread-safe update of trading bot state
                        with trading_bot.state_lock:
                            trading_bot.in_position = True
                            trading_bot.last_action = f"Manual buy at ${current_price:.2f}"
                            print(f"Updated trading bot state: in_position={trading_bot.in_position}, last_action='{trading_bot.last_action}'")
                    
                    # Add to chart data
                    trading_bot.chart_manager.add_buy_trade(current_price, coin_quantity, threshold_triggered=False)
                    
                    return jsonify({
                        "status": "success",
                        "message": f"Buy order executed successfully: {coin_quantity:.8f} {self.data_fetcher.current_symbol} at ${current_price:.2f}",
                        "price": current_price,
                        "quantity": coin_quantity,
                        "usd_amount": usd_amount,
                        "timestamp": int(time.time() * 1000)
                    })
                else:
                    return jsonify({
                        "status": "error",
                        "message": f"Buy order failed: {order.get('message', 'Unknown error')}"
                    })
                
            except Exception as e:
                print(f"Error executing buy: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({"status": "error", "message": str(e)})

        @self.app.route('/execute_sell', methods=['POST'])
        def execute_sell():
            """
            Execute a sell order from the web interface.
            
            POST parameters:
                amount: The amount to sell (either in USD or in coin units)
                amount_type: 'usd' or 'coin' to specify what the amount represents
            
            Returns:
                JSON response with order status
            """
            try:
                data = request.json
                amount = float(data.get('amount', 0))
                amount_type = data.get('amount_type', 'usd')  # Default to USD
                
                if amount <= 0:
                    return jsonify({
                        "status": "error",
                        "message": f"Invalid amount: {amount}"
                    })
                
                # Get latest price
                current_price = self.data_fetcher.get_current_price()
                if not current_price:
                    return jsonify({
                        "status": "error",
                        "message": "Could not get current price"
                    })
                
                # Calculate quantity based on amount type
                if amount_type == 'usd':
                    usd_amount = amount
                    coin_quantity = usd_amount / current_price
                else:  # amount_type == 'coin'
                    coin_quantity = amount
                    usd_amount = amount * current_price
                
                # Place the sell order
                order = self.data_fetcher.place_sell_order(self.data_fetcher.current_symbol, coin_quantity)
                
                if order and order.get("status") == "filled":
                    # Update trading bot's position status if it's tracking this coin
                    # Only check if symbols match, don't require the bot to be running
                    if hasattr(trading_bot, 'data_fetcher') and trading_bot.data_fetcher and trading_bot.data_fetcher.current_symbol == self.data_fetcher.current_symbol:
                        # Thread-safe update of trading bot state
                        with trading_bot.state_lock:
                            trading_bot.in_position = False
                            trading_bot.last_action = f"Manual sell at ${current_price:.2f}"
                            print(f"Updated trading bot state: in_position={trading_bot.in_position}, last_action='{trading_bot.last_action}'")
                    
                    # Add to chart data
                    trading_bot.chart_manager.add_sell_trade(current_price, coin_quantity, threshold_triggered=False)
                    
                    return jsonify({
                        "status": "success",
                        "message": f"Sell order executed successfully: {coin_quantity:.8f} {self.data_fetcher.current_symbol} at ${current_price:.2f}",
                        "price": current_price,
                        "quantity": coin_quantity,
                        "usd_amount": usd_amount,
                        "timestamp": int(time.time() * 1000)
                    })
                else:
                    return jsonify({
                        "status": "error",
                        "message": f"Sell order failed: {order.get('message', 'Unknown error')}"
                    })
                
            except Exception as e:
                print(f"Error executing sell: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({"status": "error", "message": str(e)})
        
    def start(self):
        """Start the Flask server in a thread"""
        try:
            print(f"\n=== Starting Web Server on port {self.port} ===")
            self.thread = threading.Thread(target=self._run_server)
            self.thread.daemon = True
            self.thread.start()
            print(f"Web server started successfully in thread: {self.thread.name}")
            print(f"Access the interface at: http://localhost:{self.port}")
            return True
        except Exception as e:
            print(f"Error starting web server: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    def shutdown(self):
        """Clean shutdown of the web server"""
        print("Shutting down web server...")
        # There's no clean way to stop a Flask server in a thread,
        # but we can try to clean up resources
        try:
            # Create a request to shutdown the server
            import requests
            try:
                requests.get(f"http://{config.HOST}:{config.PORT}/shutdown", timeout=0.1)
            except:
                pass
                
            # Force the thread to terminate (not ideal but necessary)
            if hasattr(self, 'server_thread') and self.server_thread.is_alive():
                # Cannot directly terminate threads in Python, but marking as daemon
                # ensures they'll be terminated when the main thread exits
                self.server_thread.daemon = True
                
        except Exception as e:
            print(f"Error during web server shutdown: {e}")
        
        print("Web server shutdown complete")

    def _run_server(self):
        """Run the Flask server - internal method called by start()"""
        try:
            # Determine whether to capture stdout from Flask
            if hasattr(config, 'FLASK_QUIET') and config.FLASK_QUIET:
                # Capture and discard stdout to prevent Flask startup messages
                original_stdout = sys.stdout
                sys.stdout = open('/dev/null', 'w')  # Redirect to /dev/null (Unix-like)
                
            try:
                # Try to start the server on the main port
                self.app.run(
                    host=config.HOST, 
                    port=self.port, 
                    debug=config.DEBUG, 
                    use_reloader=False,  # Don't use reloader in thread
                    threaded=True  # Enable threaded mode for better handling
                )
            except OSError as e:
                # If the port is already in use, try the backup port
                if "Address already in use" in str(e):
                    print(f"Port {self.port} is already in use. Trying backup port {config.BACKUP_PORT}...")
                    self.port = config.BACKUP_PORT
                    self.app.run(
                        host=config.HOST, 
                        port=self.port, 
                        debug=config.DEBUG, 
                        use_reloader=False,
                        threaded=True
                    )
                else:
                    # Re-raise the exception if it's not an "Address already in use" error
                    raise
                
        except Exception as e:
            print(f"Error in _run_server: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Restore stdout if we redirected it
            if hasattr(config, 'FLASK_QUIET') and config.FLASK_QUIET:
                sys.stdout.close()
                sys.stdout = original_stdout 