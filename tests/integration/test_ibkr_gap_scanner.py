"""Integration tests for IBKR gap scanner using ibind OAuth client."""

from collections.abc import Generator

import pytest

from app.config import Config
from app.scanners.gap.ibkr_gap_scanner import IBKRGapScanner


@pytest.fixture
def config() -> Config:
    """Get application config."""
    return Config()


@pytest.fixture
def ibkr_scanner(config: Config) -> Generator[IBKRGapScanner | None, None, None]:
    """Create IBKR gap scanner if credentials are available."""
    required = [
        config.ibkr_scanner.oauth_consumer_key,
        config.ibkr_scanner.oauth_access_token,
        config.ibkr_scanner.oauth_access_token_secret,
        config.ibkr_scanner.oauth_dh_prime,
    ]
    if not all(required):
        yield None
        return

    scanner = IBKRGapScanner(config.ibkr_scanner)
    scanner.connect()
    yield scanner
    scanner.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scanner_connect_and_disconnect(ibkr_scanner: IBKRGapScanner | None) -> None:
    """Test scanner connect and disconnect lifecycle."""
    if ibkr_scanner is None:
        pytest.skip("IBKR OAuth credentials not configured")

    assert ibkr_scanner.is_connected is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scanner_scan_for_gaps(ibkr_scanner: IBKRGapScanner | None) -> None:
    """Test scanner can scan for gaps."""
    if ibkr_scanner is None:
        pytest.skip("IBKR OAuth credentials not configured")

    gap_stocks = ibkr_scanner.scan_for_gaps()

    assert isinstance(gap_stocks, list)
    if len(gap_stocks) > 0:
        assert gap_stocks[0].ticker is not None
        assert gap_stocks[0].conid is not None
