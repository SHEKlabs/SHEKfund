from flask import Flask, jsonify, render_template
import threading
import config
import logging
import sys

class WebServer:
    """Class to handle the web server functionality"""
    
    def __init__(self, chart_manager, data_fetcher=None):
        """Initialize with dependencies"""
        self.chart_manager = chart_manager
        self.data_fetcher = data_fetcher
        
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
        chart_manager = self.chart_manager
        data_fetcher = self.data_fetcher
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
            
        @self.app.route('/data')
        def get_data():
            return jsonify(chart_manager.get_chart_data())
        
        @self.app.route('/update')
        def get_update():
            """Endpoint for real-time price updates"""
            if data_fetcher:
                latest_data = data_fetcher.get_latest_data()
                chart_data = chart_manager.get_chart_data()
                
                # Combine data
                response = {
                    "price": latest_data.get("price"),
                    "symbol": latest_data.get("symbol"),
                    "last_updated": latest_data.get("last_updated"),
                    "chart_data": chart_data
                }
                return jsonify(response)
            else:
                return jsonify({"error": "Data fetcher not available"}), 503
            
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