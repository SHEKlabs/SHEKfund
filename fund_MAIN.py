#Youtube tutorial Link: https://www.youtube.com/watch?v=K15KVuNvk9s 

from binance.client import Client 
import time
from datetime import datetime

API_KEY = 'vUB2Zptz3Xnu77rAyEkqU2AURgG1G9h29Kx22uxShCIZBepRznjBq3yfd1kYYAoG'
API_SECRET_KEY = 'aeDTMXgEZYVm52EbQ9CFl6yk5pSawd6WSxCU2dPirBAqQyEPQXrr9G8YDTcQxtBO'

print("~~~~ Welcome to the Main script of the shekFUND ~~~~")

client = Client(API_KEY, API_SECRET_KEY, testnet=True) #Testnet makes sure this is fake $, not real acct
client.get_account()

# Simple trading algo. Buy if below threshold, sell if above threshold
# SET THRESHOLDS !!! 
symbol = 'BTCUSDT'
buy_price_threshold = 86890
sell_price_threshold = 86990
# Amount you want to buy / sell
trade_quantity = 0.001

# Function to pull the current BTC price: 
def get_current_price(symbol):
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])
# Get the current price: 
print(get_current_price(symbol))

# ~~~ Organizing Orders ~~~ :
# Buy order:
def place_buy_order(symbol, quantity):
    order = client.order_market_buy(symbol=symbol, quantity=quantity)
    print(f"Buy Order Done: {order}")
# test placing a buy order: 
place_buy_order(symbol, trade_quantity)

# SELL order:
def place_sell_order(symbol, quantity):
    order = client.order_market_sell(symbol=symbol, quantity=quantity)
    print(f"Buy Order Done: {order}")
# test placing a sell order: 
place_sell_order(symbol, trade_quantity)

# ~~~~ TRADING BOT ~~~~
def trading_bot():
    in_position = False 

    #setup an endless look that keeps running and checking for the thresholds: 
    while True:
        now = datetime.now()
        formatted_date_time = now.strftime("< %d-%m-%Y | %H:%M:%S >")

        current_price = get_current_price(symbol)
        print(f"{formatted_date_time} Current price of {symbol}: ${current_price}")

        if not in_position:
            if current_price < buy_price_threshold:
                print(f"Price is BELOW {buy_price_threshold}. Placing BUY order.")
                place_buy_order(symbol, trade_quantity) #executes the buy order
                in_position = True  #Now the buy position is True
        else:
            if current_price > sell_price_threshold:
                print(f"Price is ABOVE {sell_price_threshold}. Placing SELL order.")
                place_sell_order(symbol, trade_quantity) #executes the sell order
                in_position = False  #Now the buy position is False
        
        #make the loop wait so it doesn't keep on running.
        time.sleep(1.5) #seconds



if __name__ == "__main__":
    trading_bot()
    
    #print(formatted_date_time)