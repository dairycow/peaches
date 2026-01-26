"""Test trading bot manager."""

import pytest

from app.bot import TradingBot, get_bot, reset_bot


def test_bot_creation():
    """Test bot can be created."""
    bot = TradingBot()
    assert bot is not None
    assert bot.gateway_service is not None
    assert bot.strategy_service is not None
    assert bot.scheduler is None
    assert bot.scanner_scheduler is None


def test_get_bot_singleton():
    """Test get_bot returns same instance."""
    reset_bot()
    bot1 = get_bot()
    bot2 = get_bot()
    assert bot1 is bot2


def test_reset_bot():
    """Test reset_bot creates new instance."""
    bot1 = get_bot()
    reset_bot()
    bot2 = get_bot()
    assert bot1 is not bot2
