import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    check_daily_loss_limit,
    check_position_limit,
    calculate_rsi,
    check_volume_confirmation,
    calculate_position_size,
    get_bars,
)


class TestStrategyFunctions:
    """Test suite for trading strategy functions."""
    
    @patch('main.api')
    def test_check_daily_loss_limit_not_exceeded(self, mock_api):
        """Test daily loss limit check when limit not exceeded."""
        mock_account = Mock()
        mock_account.equity = '10000'
        mock_account.last_equity = '10100'
        mock_api.get_account.return_value = mock_account
        
        result = check_daily_loss_limit()
        assert result is True
    
    @patch('main.api')
    def test_check_daily_loss_limit_exceeded(self, mock_api):
        """Test daily loss limit check when limit exceeded."""
        mock_account = Mock()
        mock_account.equity = '9800'
        mock_account.last_equity = '10000'
        mock_api.get_account.return_value = mock_account
        
        result = check_daily_loss_limit()
        assert result is False
    
    @patch('main.api')
    def test_check_daily_loss_limit_zero_equity(self, mock_api):
        """Test daily loss limit with zero last equity."""
        mock_account = Mock()
        mock_account.equity = '10000'
        mock_account.last_equity = '0'
        mock_api.get_account.return_value = mock_account
        
        result = check_daily_loss_limit()
        assert result is True  # Should return True due to warning
    
    @patch('main.api')
    def test_check_position_limit_not_exceeded(self, mock_api):
        """Test position limit check when under limit."""
        mock_api.list_orders.return_value = [Mock()] * 5  # 5 open orders
        
        result = check_position_limit()
        assert result is True
    
    @patch('main.api')
    def test_check_position_limit_exceeded(self, mock_api):
        """Test position limit check when exceeded."""
        mock_api.list_orders.return_value = [Mock()] * 10  # 10 open orders = at limit
        
        result = check_position_limit()
        assert result is False
    
    def test_calculate_position_size_valid(self):
        """Test position size calculation with valid inputs."""
        equity = 10000
        price = 150.00
        
        qty = calculate_position_size(equity, price, is_forex=False)
        
        # Risk 1% of $10,000 = $100; $100/150 ≈ 0 shares (or 1 if calculation allows)
        assert qty >= 0
    
    def test_calculate_position_size_forex(self):
        """Test position size calculation for forex."""
        equity = 10000
        price = 1.0850
        
        qty = calculate_position_size(equity, price, is_forex=True)
        
        # Forex should use micro lots
        assert qty >= 1000
        assert qty % 1000 == 0  # Should be multiple of 1000
    
    def test_calculate_position_size_zero_price(self):
        """Test position size calculation with zero price."""
        equity = 10000
        price = 0
        
        qty = calculate_position_size(equity, price, is_forex=False)
        
        assert qty == 0
    
    def test_calculate_position_size_negative_equity(self):
        """Test position size calculation with negative equity."""
        equity = -5000
        price = 150.00
        
        qty = calculate_position_size(equity, price, is_forex=False)
        
        # Should handle gracefully
        assert isinstance(qty, int)
    
    def test_calculate_rsi_valid_data(self):
        """Test RSI calculation with valid bar data."""
        bars = pd.DataFrame({
            'close': [100 + i for i in range(50)],
            'volume': [1000] * 50
        })
        
        rsi = calculate_rsi(bars)
        
        assert rsi is not None
        assert 0 <= rsi <= 100
    
    def test_calculate_rsi_empty_dataframe(self):
        """Test RSI calculation with empty data."""
        bars = pd.DataFrame()
        
        rsi = calculate_rsi(bars)
        
        assert rsi is None
    
    def test_check_volume_confirmation_confirmed(self):
        """Test volume confirmation when volume is high."""
        bars = pd.DataFrame({
            'close': [100] * 50,
            'volume': [1000] * 49 + [3000]  # Last bar has 3x volume
        })
        
        result = check_volume_confirmation(bars)
        
        assert result is True
    
    def test_check_volume_confirmation_not_confirmed(self):
        """Test volume confirmation when volume is normal."""
        bars = pd.DataFrame({
            'close': [100] * 50,
            'volume': [1000] * 50  # Uniform volume
        })
        
        result = check_volume_confirmation(bars)
        
        assert result is False
    
    def test_check_volume_confirmation_zero_average(self):
        """Test volume confirmation with zero average volume."""
        bars = pd.DataFrame({
            'close': [100] * 50,
            'volume': [0] * 50
        })
        
        result = check_volume_confirmation(bars)
        
        assert result is False
    
    @patch('main.api')
    def test_get_bars_valid(self, mock_api):
        """Test bar retrieval with valid response."""
        mock_bars = Mock()
        mock_bars.df = pd.DataFrame({
            'open': [100] * 50,
            'high': [105] * 50,
            'low': [95] * 50,
            'close': [102] * 50,
            'volume': [1000] * 50
        })
        mock_api.get_bars.return_value = mock_bars
        
        bars = get_bars('AAPL', is_forex=False)
        
        assert bars is not None
        assert len(bars) == 50
    
    @patch('main.api')
    def test_get_bars_empty(self, mock_api):
        """Test bar retrieval with empty response."""
        mock_bars = Mock()
        mock_bars.df = pd.DataFrame()
        mock_api.get_bars.return_value = mock_bars
        
        bars = get_bars('AAPL', is_forex=False)
        
        assert bars is None


class TestIntegration:
    """Integration tests for full strategy flow."""
    
    @patch('main.api')
    def test_full_strategy_flow_buy_signal(self, mock_api):
        """Test full strategy execution with buy signal."""
        # Setup account
        mock_account = Mock()
        mock_account.equity = '10000'
        mock_account.last_equity = '10100'
        
        # Setup bars
        bars = pd.DataFrame({
            'open': [100] * 50,
            'high': [105] * 50,
            'low': [95] * 50,
            'close': [95 + (i % 10) for i in range(50)],  # Last bar oversold
            'volume': [1000] * 49 + [3000]  # High volume on last bar
        })
        
        mock_bars = Mock()
        mock_bars.df = bars
        
        # Configure mocks
        mock_api.get_account.return_value = mock_account
        mock_api.list_orders.return_value = []  # No open orders
        mock_api.get_bars.return_value = mock_bars
        mock_api.submit_order.return_value = Mock(id='order_123')
        
        from main import run_strategy
        run_strategy('AAPL', is_forex=False)
        
        # Verify order was submitted
        assert mock_api.submit_order.called
    
    @patch('main.api')
    def test_full_strategy_flow_no_signal(self, mock_api):
        """Test full strategy execution with no buy signal."""
        # Setup account
        mock_account = Mock()
        mock_account.equity = '10000'
        mock_account.last_equity = '10100'
        
        # Setup bars (RSI not oversold)
        bars = pd.DataFrame({
            'close': [100 + i for i in range(50)],  # Uptrend
            'volume': [1000] * 50  # Normal volume
        })
        
        mock_bars = Mock()
        mock_bars.df = bars
        
        mock_api.get_account.return_value = mock_account
        mock_api.list_orders.return_value = []
        mock_api.get_bars.return_value = mock_bars
        
        from main import run_strategy
        run_strategy('AAPL', is_forex=False)
        
        # Verify order was NOT submitted
        assert not mock_api.submit_order.called


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
