// Global variable to store current price
let currentPrice = 0;

// Update current price when new data arrives
socket.on('price_update', function(data) {
    currentPrice = parseFloat(data.price);
    // ... existing code for price updates ...
    
    // Update coin amounts based on current price if USD values are filled
    if (document.getElementById('buyAmountUSD').value) {
        updateBuyAmountCoin();
    }
    if (document.getElementById('sellAmountUSD').value) {
        updateSellAmountCoin();
    }
});

// Functions to update amounts bidirectionally
function updateBuyAmountCoin() {
    const usdAmount = parseFloat(document.getElementById('buyAmountUSD').value) || 0;
    if (currentPrice > 0) {
        const coinAmount = usdAmount / currentPrice;
        document.getElementById('buyAmountCoin').value = coinAmount.toFixed(8);
    }
}

function updateBuyAmountUSD() {
    const coinAmount = parseFloat(document.getElementById('buyAmountCoin').value) || 0;
    const usdAmount = coinAmount * currentPrice;
    document.getElementById('buyAmountUSD').value = usdAmount.toFixed(2);
}

function updateSellAmountCoin() {
    const usdAmount = parseFloat(document.getElementById('sellAmountUSD').value) || 0;
    if (currentPrice > 0) {
        const coinAmount = usdAmount / currentPrice;
        document.getElementById('sellAmountCoin').value = coinAmount.toFixed(8);
    }
}

function updateSellAmountUSD() {
    const coinAmount = parseFloat(document.getElementById('sellAmountCoin').value) || 0;
    const usdAmount = coinAmount * currentPrice;
    document.getElementById('sellAmountUSD').value = usdAmount.toFixed(2);
}

// Update the buy/sell execution functions to handle coin amounts
function executeBuy() {
    const usdAmount = parseFloat(document.getElementById('buyAmountUSD').value);
    const coinAmount = parseFloat(document.getElementById('buyAmountCoin').value);
    
    // Send both values to the server
    socket.emit('execute_buy', {
        usd_amount: usdAmount,
        coin_amount: coinAmount,
        use_coin_amount: document.activeElement.id === 'buyAmountCoin' // Use coin amount if that field was last focused
    });
}

function executeSell() {
    const usdAmount = parseFloat(document.getElementById('sellAmountUSD').value);
    const coinAmount = parseFloat(document.getElementById('sellAmountCoin').value);
    
    // Send both values to the server
    socket.emit('execute_sell', {
        usd_amount: usdAmount,
        coin_amount: coinAmount,
        use_coin_amount: document.activeElement.id === 'sellAmountCoin' // Use coin amount if that field was last focused
    });
} 