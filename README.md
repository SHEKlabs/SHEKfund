# SHEKfund Trading Bot

A cryptocurrency trading bot that monitors market data from Binance and executes trades based on a threshold-based strategy.

## Features

- **Multiple Coin Support**: Configure thresholds and quantities for multiple cryptocurrencies
- **User Selection**: Choose which coin to trade at runtime
- **Live Terminal Display**: View real-time price updates and trading activity in the console
- **Web Dashboard**: Monitor price history and trades on a sleek, finance-inspired web interface
- **Threshold Visualization**: See buy and sell thresholds directly on the price chart
- **Trade Markers**: Visualize buy and sell trades as they occur

## Installation

1. Clone the repository:
```bash
git clone https://github.com/SHEKlabs/SHEKfund.git
cd SHEKfund
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your Binance API keys in the script (by default, it uses testnet):
```python
API_KEY = 'your_api_key'
API_SECRET_KEY = 'your_api_secret_key'
```

## Usage

1. Run the main script:
```bash
python fund_MAIN.py
```

2. Select a coin to trade from the list of available options

3. The bot will start monitoring prices and executing trades based on the configured thresholds

4. Open your web browser and navigate to `http://localhost:5000` to view the live trading dashboard

5. Press Ctrl+C in the terminal to stop the bot

## Configuration

You can modify the coin configurations in the script to adjust thresholds and quantities:

```python
coin_configs = {
    'BTCUSDT': {'buy_threshold': 85985, 'sell_threshold': 85990, 'quantity': 0.001},
    'ETHUSDT': {'buy_threshold': 3000, 'sell_threshold': 3100, 'quantity': 0.01},
    'LTCUSDT': {'buy_threshold': 150, 'sell_threshold': 160, 'quantity': 0.1}
}
```

## Note

This bot uses Binance's testnet by default, which means it trades with simulated funds. To trade with real funds, set `testnet=False` in the Client initialization.

## License

This project is open-source and available for personal and educational use. 