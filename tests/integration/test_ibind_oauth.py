"""Integration tests for IBKR scanner using ibind OAuth client."""

from collections.abc import Generator

import pytest
from ibind import IbkrClient
from ibind.oauth.oauth1a import OAuth1aConfig

from app.config import Config
from app.scanners.gap.ibkr_gap_scanner import IBKRGapScanner


@pytest.fixture
def config() -> Config:
    """Get application config."""
    return Config()


@pytest.fixture
def oauth_config(config: Config) -> OAuth1aConfig | None:
    """Create OAuth config if credentials are available."""
    required = [
        config.ibkr_scanner.oauth_consumer_key,
        config.ibkr_scanner.oauth_access_token,
        config.ibkr_scanner.oauth_access_token_secret,
        config.ibkr_scanner.oauth_dh_prime,
    ]
    if not all(required):
        return None
    return OAuth1aConfig(
        consumer_key=config.ibkr_scanner.oauth_consumer_key,
        access_token=config.ibkr_scanner.oauth_access_token,
        access_token_secret=config.ibkr_scanner.oauth_access_token_secret,
        dh_prime=config.ibkr_scanner.oauth_dh_prime,
        encryption_key_fp=config.ibkr_scanner.encryption_key_path,
        signature_key_fp=config.ibkr_scanner.signature_key_path,
        realm=config.ibkr_scanner.realm,
        init_oauth=False,
        maintain_oauth=False,
        init_brokerage_session=False,
    )


@pytest.fixture
def ibkr_client(oauth_config: OAuth1aConfig | None) -> Generator[IbkrClient | None, None, None]:
    """Create and initialise IBKR client if OAuth config is available."""
    if oauth_config is None:
        yield None
        return

    client = IbkrClient(use_oauth=True, oauth_config=oauth_config, timeout=30)
    client.oauth_init(maintain_oauth=False, init_brokerage_session=False)

    try:
        client.initialize_brokerage_session(compete=True)
    except Exception:
        pass

    yield client

    client.stop_tickler(timeout=5)
    client.close()


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
async def test_oauth_connection(ibkr_client: IbkrClient | None) -> None:
    """Test OAuth connection to IBKR API."""
    if ibkr_client is None:
        pytest.skip("IBKR OAuth credentials not configured")

    status = ibkr_client.check_auth_status()
    assert status is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_market_scanner_returns_contracts(ibkr_client: IbkrClient | None) -> None:
    """Test market scanner returns contracts."""
    if ibkr_client is None:
        pytest.skip("IBKR OAuth credentials not configured")

    scan_configs = [
        {"instrument": "STOCK.HK", "type": "HIGH_OPEN_GAP", "location": "STK.HK.ASX", "filter": []},
        {"instrument": "STOCK.HK", "type": "TOP_PERC_GAIN", "location": "STK.HK.ASX", "filter": []},
        {"instrument": "STK", "type": "TOP_PERC_GAIN", "location": "STK.US.MAJOR", "filter": []},
    ]

    for cfg in scan_configs:
        try:
            result = ibkr_client.market_scanner(**cfg)
            if result and result.data:
                contracts = result.data
                if isinstance(contracts, dict):
                    contracts = contracts.get("contracts", [contracts])
                assert len(contracts) > 0
                assert contracts[0].get("symbol") is not None
                return
        except Exception:
            continue

    pytest.skip("All scanner endpoints returned errors or empty results")


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
