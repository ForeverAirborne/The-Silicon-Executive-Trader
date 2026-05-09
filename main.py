import alpaca_trade_api as tradeapi
import pandas as pd
from ta.momentum import RSIIndicator
import os
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- SECURE CONFIGURATION ---
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
BASE_URL = os.getenv('BASE_URL', 'https://paper-api.alpaca.markets')

if not API_KEY or not SECRET_KEY:
    raise ValueError("API_KEY and SECRET_KEY must be set in environment variables")

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL)

# --- CONFIGURATION CONSTANTS ---
DAILY_LOSS_LIMIT = 0.02  # 2% daily loss threshold
RISK_PER_TRADE = 0.01    # 1% of equity per trade
RSI_PERIOD = 14
RSI_OVERSOLD = 30
VOLUME_MULTIPLIER = 1.2
STOP_LOSS_PCT = 0.01     # 1% stop loss
TAKE_PROFIT_PCT = 0.02   # 2% take profit
MAX_CONCURRENT_ORDERS = 10

def get_account_metrics():
    """Fetch and validate account metrics."""
    try:
        account = api.get_account()
        equity = float(account.equity)
        last_equity = float(account.last_equity)
        
        if last_equity == 0:
            logger.warning("Last equity is zero; cannot calculate daily loss")
            return equity, 0.0
        
        daily_loss = (last_equity - equity) / last_equity
        return equity, daily_loss
    except Exception as e:
        logger.error(f"Failed to fetch account metrics: {e}")
        raise

def check_daily_loss_limit(daily_loss):
    """Verify trading hasn't exceeded daily loss threshold."""
    if daily_loss >= DAILY_LOSS_LIMIT:
        logger.warning(f"Daily loss limit reached ({daily_loss:.2%}). Trading suspended.")
        return False
    return True

def fetch_bars(symbol, limit=50):
    """Fetch OHLCV bars for analysis."""
    try:
        timeframe = tradeapi.TimeFrame.Minute
        bars = api.get_bars(symbol, timeframe, limit=limit)
        
        if bars is None or len(bars) == 0:
            logger.warning(f"No bars returned for {symbol}")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame({
            'open': [b.o for b in bars],
            'high': [b.h for b in bars],
            'low': [b.l for b in bars],
            'close': [b.c for b in bars],
            'volume': [b.v for b in bars]
        })
        return df
    except Exception as e:
        logger.error(f"Failed to fetch bars for {symbol}: {e}")
        return None

def calculate_rsi(close_prices, period=RSI_PERIOD):
    """Calculate RSI indicator."""
    try:
        rsi_indicator = RSIIndicator(close=close_prices, window=period)
        rsi_values = rsi_indicator.rsi()
        
        if rsi_values.isna().all():
            logger.warning("RSI calculation resulted in all NaN values")
            return None
        
        return rsi_values.iloc[-1]
    except Exception as e:
        logger.error(f"Failed to calculate RSI: {e}")
        return None

def check_position_limit():
    """Verify we haven't exceeded max concurrent orders."""
    try:
        open_orders = api.list_orders(status='open')
        if len(open_orders) >= MAX_CONCURRENT_ORDERS:
            logger.info(f"Max concurrent orders ({MAX_CONCURRENT_ORDERS}) reached. Skipping new entries.")
            return False
        return True
    except Exception as e:
        logger.error(f"Failed to check position limit: {e}")
        return False

def calculate_position_size(equity, entry_price):
    """Calculate position size based on 1% risk rule."""
    if entry_price <= 0:
        logger.error("Invalid entry price for position sizing")
        return 0
    
    qty = int((equity * RISK_PER_TRADE) / entry_price)
    return max(qty, 1)  # Minimum 1 share

def submit_bracket_order(symbol, qty, entry_price):
    """Submit a market order with stop-loss and take-profit."""
    try:
        stop_price = round(entry_price * (1 - STOP_LOSS_PCT), 2)
        profit_price = round(entry_price * (1 + TAKE_PROFIT_PCT), 2)
        
        # Submit bracket order: buy + stop loss + take profit
        order = api.submit_order(
            symbol=symbol,
            qty=qty,
            side='buy',
            type='market',
            time_in_force='gtc',
            order_class='bracket',
            stop_loss={'stop_price': stop_price},
            take_profit={'limit_price': profit_price}
        )
        
        logger.info(f"✓ Order submitted: {symbol} x{qty} | Entry: ${entry_price:.2f} | SL: ${stop_price:.2f} | TP: ${profit_price:.2f}")
        return order
    except Exception as e:
        logger.error(f"Failed to submit order for {symbol}: {e}")
        return None

def run_strategy(symbol):
    """Execute RSI + Volume trading strategy."""
    try:
        logger.info(f"--- Scanning {symbol} ---")
        
        # 1. CHECK DAILY LOSS LIMIT
        equity, daily_loss = get_account_metrics()
        if not check_daily_loss_limit(daily_loss):
            return False
        
        # 2. CHECK POSITION LIMIT
        if not check_position_limit():
            return False
        
        # 3. FETCH MARKET DATA
        bars = fetch_bars(symbol)
        if bars is None or bars.empty:
            logger.warning(f"No data available for {symbol}")
            return False
        
        # 4. CALCULATE INDICATORS
        rsi = calculate_rsi(bars['close'])
        if rsi is None:
            return False
        
        current_vol = bars['volume'].iloc[-1]
        avg_vol = bars['volume'].mean()
        entry_price = bars['close'].iloc[-1]
        
        logger.info(f"{symbol}: RSI={rsi:.2f}, Vol={current_vol:.0f} (avg: {avg_vol:.0f})")
        
        # 5. TRADING LOGIC: RSI Oversold + Volume Confirmation
        if rsi < RSI_OVERSOLD and current_vol > (avg_vol * VOLUME_MULTIPLIER):
            qty = calculate_position_size(equity, entry_price)
            
            if qty > 0:
                submit_bracket_order(symbol, qty, entry_price)
                return True
        else:
            logger.debug(f"{symbol} did not meet entry criteria (RSI: {rsi:.2f}, Vol ratio: {current_vol/avg_vol:.2f}x)")
        
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error scanning {symbol}: {e}", exc_info=True)
        return False

# --- EXECUTION ---
if __name__ == "__main__":
    symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT']
    
    logger.info("=" * 60)
    logger.info("Starting Silicon Executive Trader Strategy")
    logger.info(f"Account Equity: ${get_account_metrics()[0]:.2f}")
    logger.info("=" * 60)
    
    for symbol in symbols:
        run_strategy(symbol)
    
    logger.info("=" * 60)
    logger.info("Strategy execution complete")
    logger.info("=" * 60)
