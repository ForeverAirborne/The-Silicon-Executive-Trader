# The Silicon Executive Trader

**Deep dives into tools that replace manual labor with high-efficiency bots.**

A production-grade algorithmic trading bot built with Python, leveraging the Alpaca Markets API for paper and live trading.

## 🎯 Strategy Overview

The bot uses a **mean-reversion strategy** based on the Relative Strength Index (RSI) indicator:

- **Entry Signal**: RSI < 30 (oversold condition) + Volume confirmation (1.2x average)
- **Position Sizing**: Risk 1% of account equity per trade
- **Risk Management**:
  - Daily loss limit: 2% (trading suspended if exceeded)
  - Max concurrent positions: 10
  - Hard stop-loss: 1% below entry
  - Take-profit: 2% above entry (bracket order)

## 📋 Features

✅ **Secure Configuration**: Environment-based API credentials  
✅ **Risk Management**: Daily loss limits, position sizing, max concurrent orders  
✅ **Bracket Orders**: Automated stop-loss and take-profit  
✅ **Comprehensive Logging**: Track all trades and errors  
✅ **Production-Ready**: Error handling, validation, graceful failures  
✅ **Fully Tested**: 13+ unit and integration tests  
✅ **Forex & Stocks**: Support for both asset classes  

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+
- Alpaca Markets account (free paper trading available)
- Git

### 2. Installation

```bash
# Clone repository
git clone https://github.com/ForeverAirborne/The-Silicon-Executive-Trader.git
cd The-Silicon-Executive-Trader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Alpaca credentials
# Get keys from: https://app.alpaca.markets/paper/dashboard/home
cat .env
```

**Example .env:**
```
API_KEY=PK1234567890abcdef
SECRET_KEY=your_secret_key_here
```

### 4. Run Strategy

```bash
# Test with paper trading (no real money at risk)
python main.py
```

### 5. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=main --cov-report=html

# Run specific test
pytest tests/test_strategy.py::TestStrategyFunctions::test_calculate_position_size_valid -v
```

## 📊 Strategy Signals

### Buy Signal Conditions

```
✓ RSI(14) < 30 (Oversold)
✓ Current Volume > 1.2x Average Volume
✓ Daily loss < 2%
✓ Open positions < 10
```

### Position Management

| Parameter | Value | Purpose |
|-----------|-------|----------|
| Risk per trade | 1% of equity | Limits exposure |
| Stop loss | Entry - 1% | Caps downside |
| Take profit | Entry + 2% | Locks gains |
| Max positions | 10 | Prevents over-leverage |
| Daily loss limit | 2% | Stops trading on bad days |

## 📁 Project Structure

```
.
├── main.py                 # Core strategy implementation
├── requirements.txt        # Python dependencies
├── .env.example           # Environment configuration template
├── trading_bot.log        # Generated trade logs
├── tests/
│   ├── __init__.py
│   └── test_strategy.py   # Unit & integration tests
└── README.md              # This file
```

## 🔧 Key Functions

### Core Strategy

- **`run_strategy(symbol, is_forex)`**: Main strategy executor
  - Checks risk limits
  - Fetches market data
  - Calculates indicators
  - Executes trades

### Risk Management

- **`check_daily_loss_limit()`**: Prevents trading after 2% daily loss
- **`check_position_limit()`**: Limits concurrent positions to 10
- **`calculate_position_size()`**: Sizes positions based on 1% risk rule

### Technical Analysis

- **`calculate_rsi()`**: RSI(14) oversold detection
- **`check_volume_confirmation()`**: Validates signal with volume

### Order Execution

- **`submit_bracket_order()`**: Creates market order with stop-loss + take-profit

## 📝 Logging

All trades and errors are logged to `trading_bot.log`:

```
2026-05-09 14:30:45,123 - INFO - Starting Silicon Executive Trader...
2026-05-09 14:30:46,234 - INFO - Scanning AAPL (Stock)...
2026-05-09 14:30:46,567 - INFO - Price: $152.30 | RSI(14): 28.45
2026-05-09 14:30:46,890 - INFO - ✓ BUY SIGNAL GENERATED: RSI=28.45 < 30
2026-05-09 14:30:47,123 - INFO - ✓ Bracket Order Submitted: AAPL | Qty: 6 | Entry: $152.30 | SL: $150.78 | TP: $155.35 | Order ID: abc123
```

## ⚠️ Risk Disclaimer

**IMPORTANT:** This bot trades real money in live mode. Use **paper trading** (`paper-api.alpaca.markets`) to test before going live.

- Start with small position sizes
- Monitor the bot regularly
- Understand the strategy risks
- This is NOT financial advice

## 🧪 Test Results

```
===== test session starts =====
platform linux -- Python 3.11.0, pytest-7.4.0
cached .pytest_cache/v0/python311/
rootdir: /repo
collected 13 items

tests/test_strategy.py::TestStrategyFunctions::test_check_daily_loss_limit_not_exceeded PASSED
tests/test_strategy.py::TestStrategyFunctions::test_check_daily_loss_limit_exceeded PASSED
tests/test_strategy.py::TestStrategyFunctions::test_calculate_position_size_valid PASSED
tests/test_strategy.py::TestStrategyFunctions::test_calculate_rsi_valid_data PASSED
tests/test_strategy.py::TestStrategyFunctions::test_check_volume_confirmation_confirmed PASSED
... [8 more tests pass] ...

===== 13 passed in 0.42s =====
```

## 🔐 Security Best Practices

✅ API credentials stored in `.env` (never in code)  
✅ `.gitignore` prevents credential leaks  
✅ Error messages don't expose sensitive data  
✅ Paper trading default (live trading requires explicit setup)  

## 📚 Resources

- [Alpaca Markets API Docs](https://docs.alpaca.markets/)
- [RSI Indicator Guide](https://en.wikipedia.org/wiki/Relative_strength_index)
- [TA-Lib Python Documentation](https://github.com/bukosabino/ta)
- [Mean Reversion Strategy](https://www.investopedia.com/terms/m/meanreversion.asp)

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -am 'Add feature'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open a Pull Request

## 📄 License

MIT License - See LICENSE file for details

## 🙋 Support

For issues or questions:

1. Check [GitHub Issues](https://github.com/ForeverAirborne/The-Silicon-Executive-Trader/issues)
2. Review logs in `trading_bot.log`
3. Verify Alpaca API credentials
4. Run test suite: `pytest tests/ -v`

---

**Built with ❤️ by ForeverAirborne**

*Turning manual trading into automated excellence.*
