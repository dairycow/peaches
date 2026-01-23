"""Integration tests for ASX price-sensitive scanner."""

import pytest

from app.scanners.asx.price_sensitive import ASXPriceSensitiveScanner, ScannerConfig


@pytest.mark.integration
@pytest.mark.asyncio
async def test_asx_price_sensitive_scanner_real_url():
    """Test scanner with real ASX URL."""
    config = ScannerConfig(
        url="https://www.asx.com.au/asx/v2/statistics/prevBusDayAnns.do",  # Works on weekends too
        timeout=30,
        exclude_tickers=[],
        min_ticker_length=1,
        max_ticker_length=10,
    )

    scanner = ASXPriceSensitiveScanner(config)
    result = await scanner.execute()

    assert result.success
    assert len(result.data) > 0
    assert "announcements" in result.message.lower()
    assert result.error is None

    for item in result.data:
        assert "ticker" in item
        assert "headline" in item
        assert "timestamp" in item
        assert len(item["ticker"]) >= 1
        assert len(item["headline"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_asx_price_sensitive_scanner_with_exclusions():
    """Test scanner with ticker exclusions."""
    config = ScannerConfig(
        url="https://www.asx.com.au/asx/v2/statistics/prevBusDayAnns.do",
        timeout=30,
        exclude_tickers=["BHP", "CBA"],
        min_ticker_length=1,
        max_ticker_length=10,
    )

    scanner = ASXPriceSensitiveScanner(config)
    result = await scanner.execute()

    assert result.success
    tickers = [item["ticker"] for item in result.data]
    assert "BHP" not in tickers
    assert "CBA" not in tickers


@pytest.mark.integration
@pytest.mark.asyncio
async def test_asx_price_sensitive_scanner_ticker_length_filter():
    """Test scanner with ticker length constraints."""
    config = ScannerConfig(
        url="https://www.asx.com.au/asx/v2/statistics/prevBusDayAnns.do",
        timeout=30,
        exclude_tickers=[],
        min_ticker_length=2,
        max_ticker_length=4,
    )

    scanner = ASXPriceSensitiveScanner(config)
    result = await scanner.execute()

    assert result.success
    for item in result.data:
        ticker = item["ticker"]
        assert 2 <= len(ticker) <= 4


@pytest.mark.integration
@pytest.mark.asyncio
async def test_asx_price_sensitive_scanner_name():
    """Test scanner name property."""
    config = ScannerConfig(
        url="https://www.asx.com.au/asx/v2/statistics/prevBusDayAnns.do",
        timeout=30,
        exclude_tickers=[],
        min_ticker_length=1,
        max_ticker_length=10,
    )

    scanner = ASXPriceSensitiveScanner(config)
    assert scanner.name == "asx_price_sensitive"
