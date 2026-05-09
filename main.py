import alpaca_trade_api as tradeapi
import pandas as pd
from ta.momentum import RSIIndicator
import os
import logging
from typing import Optional, Dict
from datetime import datetime

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- SECURE CONFIGURATION ---
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
BASE_URL = 'https://paper-api.alpaca.markets'

if not API_KEY or not SECRET_KEY:
    logger.error("API credentials not found in environment variables")
    raise ValueError("Missing API_KEY or SECRET_KEY in .env")

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL)

# --- CONFIGURATION CONSTANTS ---
MAX_CONCURRENT_POSITIONS = 10
DAILY_LOSS_LIMIT = 0.02  # 2%
RISK_PER_TRADE = 0.01   # 1%
RSI_OVERSOLD = 30
VOLUME_MULTIPLIER = 1.2
STOP_LOSS_PCT = 0.99    # 1% below entry
TAKE_PROFIT_PCT = 1.02  # 2% above entry
RSI_WINDOW = 14
LOOKBACK_BARS = 50


def check_daily_loss_limit() -> bool:
    """Check if daily loss threshold has been exceeded."""
    try:
        account = api.get_account()
        equity = float(account.equity)
        last_equity = float(account.last_equity)
        
        if last_equity == 0:
            logger.warning("Cannot calculate daily loss: last_equity is 0")
            return True
        
        daily_loss = (last_equity - equity) / last_equity
        
        if daily_loss >= DAILY_LOSS_LIMIT:
            logger.warning(f"ALARM: Daily loss limit reached ({daily_loss:.2%}). Trading suspended.")
            return False
        
        logger.info(f"Daily P&L: {daily_loss:.2%} (Limit: {DAILY_LOSS_LIMIT:.2%})")
        return True
        
    except Exception as e:
        logger.error(f"Error checking daily loss limit: {e}")
        return False


def check_position_limit() -> bool:
    """Check if maximum concurrent positions limit has been reached."""
    try:
        open_orders = api.list_orders(status='open')
        if len(open_orders) >= MAX_CONCURRENT_POSITIONS:
            logger.warning(f"Position limit reached: {len(open_orders)}/{MAX_CONCURRENT_POSITIONS}")
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking position limit: {e}")
        return False


def get_bars(symbol: str, is_forex: bool = False) -> Optional[pd.DataFrame]:
    """Fetch historical bar data for the symbol."""
    try:
        timeframe = tradeapi.TimeFrame.Minute
        bars = api.get_bars(symbol, timeframe, limit=LOOKBACK_BARS).df
        
        if bars.empty:
            logger.warning(f"No bar data available for {symbol}")
            return None
        
        return bars
        
    except Exception as e:
        logger.error(f"Error fetching bars for {symbol}: {e}")
        return None


def calculate_rsi(bars: pd.DataFrame) -> Optional[float]:
    """Calculate RSI indicator."""
    try:
        if bars is None or bars.empty or 'close' not in bars.columns:
            logger.warning("Invalid bar data for RSI calculation")
            return None
        
        rsi = RSIIndicator(close=bars['close'], window=RSI_WINDOW).rsi()
        current_rsi = rsi.iloc[-1]
        
        if pd.isna(current_rsi):
            logger.warning("RSI calculation resulted in NaN")
            return None
        
        return current_rsi
        
    except Exception as e:
        logger.error(f"Error calculating RSI: {e}")
        return None


def check_volume_confirmation(bars: pd.DataFrame) -> bool:
    """Check if current volume confirms the signal."""
    try:
        if bars is None or bars.empty or 'volume' not in bars.columns:
            logger.warning("Invalid bar data for volume check")
            return False
        
        current_vol = bars['volume'].iloc[-1]
        avg_vol = bars['volume'].mean()
        
        if avg_vol == 0:
            logger.warning("Average volume is zero")
            return False
        
        volume_ratio = current_vol / avg_vol
        confirmation = volume_ratio > VOLUME_MULTIPLIER
        
        logger.debug(f"Volume: {current_vol:.0f}, Avg: {avg_vol:.0f}, Ratio: {volume_ratio:.2f}x (Threshold: {VOLUME_MULTIPLIER}x)")
        return confirmation
        
    except Exception as e:
        logger.error(f"Error checking volume: {e}")
        return False


def calculate_position_size(equity: float, price: float, is_forex: bool = False) -> int:
    """Calculate position size based on risk management rules."""
    try:
        if price <= 0:
            logger.error(f"Invalid price for position sizing: {price}")
            return 0
        
        if is_forex:
            # Forex: Use micro lot (1000 units) as base, scale by equity
            risk_amount = equity * RISK_PER_TRADE
            qty = max(1000, int((risk_amount / price) * 1000) // 1000)
        else:
            # Stocks: Calculate shares based on 1% risk
            risk_amount = equity * RISK_PER_TRADE
            qty = int(risk_amount / price)
        
        if qty <= 0:
            logger.warning(f"Calculated position size is {qty}, must be > 0")
            return 0
        
        logger.info(f"Position size calculated: {qty} units (Risk: {RISK_PER_TRADE:.2%} of ${equity:.2f})")
        return qty
        
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return 0


def submit_bracket_order(symbol: str, qty: int, entry_price: float, is_forex: bool = False) -> bool:
    """Submit a bracket order with stop-loss and take-profit."""
    try:
        if qty <= 0 or entry_price <= 0:
            logger.error(f"Invalid order parameters: qty={qty}, price={entry_price}")
            return False
        
        stop_price = round(entry_price * STOP_LOSS_PCT, 4 if is_forex else 2)
        limit_price = round(entry_price * TAKE_PROFIT_PCT, 4 if is_forex else 2)
        
        # Alpaca bracket order format
        order = api.submit_order(
            symbol=symbol,
            qty=qty,
            side='buy',
            type='market',
            time_in_force='gtc',
            order_class='bracket',
            take_profit={'limit_price': limit_price},
            stop_loss={'stop_price': stop_price}
        )
        
        logger.info(
            f"✓ Bracket Order Submitted: {symbol} | "
            f"Qty: {qty} | Entry: ${entry_price:.2f} | "
            f"SL: ${stop_price:.2f} | TP: ${limit_price:.2f} | "
            f"Order ID: {order.id}"
        )
        return True
        
    except Exception as e:
        logger.error(f"Error submitting bracket order for {symbol}: {e}")
        return False


def run_strategy(symbol: str, is_forex: bool = False) -> None:
    """Execute the trading strategy for a given symbol."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Scanning {symbol} {'(Forex)' if is_forex else '(Stock)'}...")
    logger.info(f"{'='*60}")
    
    try:
        # 1. CHECK RISK LIMITS
        if not check_daily_loss_limit():
            logger.warning(f"Skipping {symbol}: Daily loss limit exceeded")
            return
        
        if not check_position_limit():
            logger.warning(f"Skipping {symbol}: Max concurrent positions reached")
            return
        
        # 2. FETCH DATA
        bars = get_bars(symbol, is_forex)
        if bars is None:
            return
        
        # 3. CALCULATE INDICATORS
        rsi = calculate_rsi(bars)
        if rsi is None:
            return
        
        current_price = bars['close'].iloc[-1]
        logger.info(f"Price: ${current_price:.2f} | RSI(14): {rsi:.2f}")
        
        # 4. SIGNAL GENERATION: RSI Oversold + Volume Confirmation
        if rsi < RSI_OVERSOLD and check_volume_confirmation(bars):
            logger.info(f"✓ BUY SIGNAL GENERATED: RSI={rsi:.2f} < {RSI_OVERSOLD}")
            
            # Get account equity
            account = api.get_account()
            equity = float(account.equity)
            
            # 5. POSITION SIZING
            qty = calculate_position_size(equity, current_price, is_forex)
            if qty <= 0:
                logger.warning(f"Skipping {symbol}: Invalid position size")
                return
            
            # 6. SUBMIT BRACKET ORDER
            if submit_bracket_order(symbol, qty, current_price, is_forex):
                logger.info(f"SUCCESS: Trade executed for {symbol}")
            else:
                logger.error(f"FAILED: Could not execute trade for {symbol}")
        else:
            logger.debug(
                f"Signal not met: RSI={rsi:.2f} (threshold: {RSI_OVERSOLD}) | "
                f"Volume Confirmed: {check_volume_confirmation(bars)}"
            )
    
    except Exception as e:
        logger.error(f"Unexpected error in strategy for {symbol}: {e}")


# --- EXECUTION ---
if __name__ == "__main__":
    logger.info("Starting Silicon Executive Trader...")
    logger.info(f"Base URL: {BASE_URL}")
    logger.info(f"Risk per trade: {RISK_PER_TRADE:.2%}")
    logger.info(f"Daily loss limit: {DAILY_LOSS_LIMIT:.2%}")
    logger.info(f"Max concurrent positions: {MAX_CONCURRENT_POSITIONS}")
    
    try:
        # Scan equity markets
        run_strategy('AAPL')  # High-Volume Stock
        run_strategy('TSLA')  # Tech Stock
        
        # Scan forex pairs
        run_strategy('EUR/USD', is_forex=True)  # Major Forex Pair
        
        logger.info("\nStrategy scan complete.")
    
    except KeyboardInterrupt:
        logger.info("Trading bot stopped by user.")
    except Exception as e:
        logger.critical(f"Critical error in main execution: {e}")
