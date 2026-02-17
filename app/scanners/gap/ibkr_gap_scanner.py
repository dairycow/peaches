"""IBKR gap scanner using ibind OAuth client."""

from datetime import datetime

from ibind import IbkrClient
from ibind.oauth.oauth1a import OAuth1aConfig
from loguru import logger

from app.config import IBKRScannerConfig
from app.scanners.gap.models import GapStock


class IBKRGapScanner:
    """IBKR gap scanner using ibind for OAuth authentication.

    Scans ASX stocks for gap up patterns using IBKR's market scanner API.
    """

    SCAN_CONFIGS = [
        {"instrument": "STOCK.HK", "type": "HIGH_OPEN_GAP", "location": "STK.HK.ASX", "filter": []},
        {"instrument": "STOCK.HK", "type": "TOP_PERC_GAIN", "location": "STK.HK.ASX", "filter": []},
        {
            "instrument": "STOCK.HK",
            "type": "TOP_OPEN_PERC_GAIN",
            "location": "STK.HK.ASX",
            "filter": [],
        },
    ]

    def __init__(self, config: IBKRScannerConfig) -> None:
        """Initialize the scanner.

        Args:
            config: IBKR scanner configuration
        """
        self.config = config
        self._client: IbkrClient | None = None

    def _create_oauth_config(self) -> OAuth1aConfig:
        """Create OAuth configuration from app config.

        Returns:
            OAuth1aConfig instance
        """
        return OAuth1aConfig(
            consumer_key=self.config.oauth_consumer_key,
            access_token=self.config.oauth_access_token,
            access_token_secret=self.config.oauth_access_token_secret,
            dh_prime=self.config.oauth_dh_prime,
            encryption_key_fp=self.config.encryption_key_path,
            signature_key_fp=self.config.signature_key_path,
            realm=self.config.realm,
            init_oauth=False,
            maintain_oauth=False,
            init_brokerage_session=False,
        )

    def connect(self) -> None:
        """Initialize OAuth and brokerage session."""
        if self._client is not None:
            return

        logger.info("Initializing IBKR client with OAuth...")

        oauth_config = self._create_oauth_config()
        self._client = IbkrClient(
            use_oauth=True,
            oauth_config=oauth_config,
            timeout=self.config.timeout,
        )

        self._client.oauth_init(
            maintain_oauth=False,
            init_brokerage_session=False,
        )

        try:
            self._client.initialize_brokerage_session(compete=True)
            logger.info("IBKR brokerage session initialized")
        except Exception as e:
            logger.warning(f"Brokerage session init note: {e}")

        logger.info("IBKR client connected")

    def disconnect(self) -> None:
        """Disconnect and cleanup client."""
        if self._client is None:
            return

        logger.info("Disconnecting IBKR client...")
        try:
            self._client.stop_tickler(timeout=5)
            self._client.close()
        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")
        finally:
            self._client = None

        logger.info("IBKR client disconnected")

    def scan_for_gaps(self) -> list[GapStock]:
        """Scan for ASX stocks with gaps.

        Returns:
            List of GapStock objects sorted by gap percentage
        """
        if self._client is None:
            raise RuntimeError("Scanner not connected. Call connect() first.")

        logger.info(f"Scanning for ASX gaps >= {self.config.gap_threshold}%")

        scan_result = None

        for cfg in self.SCAN_CONFIGS:
            scan_type = cfg["type"]
            location = cfg["location"]
            logger.debug(f"Trying scanner: {scan_type} on {location}")

            try:
                scan_result = self._client.market_scanner(**cfg)
                if scan_result and scan_result.data:
                    logger.info(f"Scanner {scan_type} succeeded")
                    break
            except Exception as e:
                err_str = str(e)
                if "503" in err_str:
                    logger.debug(f"Scanner {scan_type} unavailable (503)")
                else:
                    logger.warning(f"Scanner {scan_type} failed: {e}")
                continue

        if not scan_result or not scan_result.data:
            logger.warning("All scanner attempts returned no results")
            return []

        contracts = scan_result.data
        if isinstance(contracts, dict):
            contracts = contracts.get("contracts", [contracts])

        logger.info(f"Scanner returned {len(contracts)} contracts")

        gap_stocks = []
        for contract in contracts:
            gap_stock = self._parse_contract(contract)
            if gap_stock and gap_stock.gap_percent >= self.config.gap_threshold:
                gap_stocks.append(gap_stock)

        gap_stocks.sort(key=lambda x: x.gap_percent, reverse=True)

        logger.info(f"Found {len(gap_stocks)} stocks with gap >= {self.config.gap_threshold}%")
        return gap_stocks

    def _parse_contract(self, contract: dict) -> GapStock | None:
        """Parse scanner contract result into GapStock.

        Args:
            contract: Contract dictionary from scanner

        Returns:
            GapStock if valid, None otherwise
        """
        symbol = contract.get("symbol")
        conid = contract.get("conid", contract.get("con_id"))

        if not symbol or not conid:
            return None

        try:
            return GapStock(
                ticker=str(symbol),
                conid=int(conid),
                gap_percent=0.0,
                company_name=contract.get("companyName", contract.get("company_name")),
                exchange=contract.get("listing_exchange"),
                timestamp=datetime.now(),
            )
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse contract {symbol}: {e}")
            return None

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._client is not None
