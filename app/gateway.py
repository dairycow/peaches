"""IB Gateway connection wrapper with vn.py."""

import asyncio

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import (
    AccountData,
    CancelRequest,
    ContractData,
    OrderData,
    OrderRequest,
    PositionData,
    SubscribeRequest,
    TradeData,
)
from vnpy_ib import IbGateway

from app.config import config


class IBGatewayConnection:
    """IB Gateway connection manager using vn.py."""

    def __init__(self) -> None:
        """Initialize IB Gateway connection."""
        self.event_engine: EventEngine | None = None
        self.main_engine: MainEngine | None = None
        self.gateway: BaseGateway | None = None
        self.connected = False
        self._reconnect_attempts = 0

    async def connect(self) -> None:
        """Connect to IB Gateway.

        Raises:
            ConnectionError: If connection fails after retries
        """
        try:
            await self._connect_with_retry()
            logger.info("Successfully connected to IB Gateway")
        except Exception as e:
            logger.error(f"Failed to connect to IB Gateway: {e}")
            raise ConnectionError(f"IB Gateway connection failed: {e}") from None

    @retry(
        stop=stop_after_attempt(config.gateway.max_reconnect_attempts),
        wait=wait_exponential(multiplier=1, min=config.gateway.reconnect_interval, max=60),
        reraise=True,
    )
    async def _connect_with_retry(self) -> None:
        """Connect to IB Gateway with retry logic.

        Raises:
            ConnectionError: If connection fails
        """
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)

        self.main_engine.add_gateway(IbGateway)

        setting: dict[str, int | str] = {
            "TWS地址": config.gateway.host,
            "TWS端口": int(config.gateway.port),
            "客户号": config.gateway.client_id,
            "交易账户": "",
        }

        try:
            if self.main_engine is None:
                raise RuntimeError("Main engine not initialized")

            main_engine = self.main_engine
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: main_engine.connect(setting, "IB")
            )

            await self._wait_for_connection(timeout=config.gateway.connect_timeout)

            self.connected = True
            self._reconnect_attempts = 0

        except Exception as e:
            self._reconnect_attempts += 1
            logger.warning(f"Connection attempt {self._reconnect_attempts} failed: {e}")

            if self.gateway:
                await asyncio.get_event_loop().run_in_executor(None, self.gateway.close)

            if self.event_engine:
                await asyncio.get_event_loop().run_in_executor(None, self.event_engine.stop)

            raise

    async def _wait_for_connection(self, timeout: int) -> None:
        """Wait for IB Gateway connection to be established.

        Args:
            timeout: Maximum wait time in seconds

        Raises:
            TimeoutError: If connection not established within timeout
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            await asyncio.sleep(0.5)

            if self.main_engine and self.main_engine.get_gateway("IB"):
                self.gateway = self.main_engine.get_gateway("IB")
                if self.connected:
                    return

        raise TimeoutError(f"IB Gateway connection timeout after {timeout} seconds")

    async def disconnect(self) -> None:
        """Disconnect from IB Gateway."""
        try:
            if self.gateway:
                await asyncio.get_event_loop().run_in_executor(None, self.gateway.close)

            if self.event_engine:
                await asyncio.get_event_loop().run_in_executor(None, self.event_engine.stop)

            self.connected = False
            logger.info("Disconnected from IB Gateway")

        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def subscribe(self, req: SubscribeRequest) -> None:
        """Subscribe to market data.

        Args:
            req: Subscription request
        """
        if not self.gateway or not self.connected:
            raise ConnectionError("Not connected to IB Gateway")

        self.gateway.subscribe(req)

    def send_order(self, req: OrderRequest) -> str:
        """Send order to IB Gateway.

        Args:
            req: Order request

        Returns:
            Order ID string
        """
        if not self.gateway or not self.connected:
            raise ConnectionError("Not connected to IB Gateway")

        return self.gateway.send_order(req)

    def cancel_order(self, req: CancelRequest) -> None:
        """Cancel order.

        Args:
            req: Cancel request
        """
        if not self.gateway or not self.connected:
            raise ConnectionError("Not connected to IB Gateway")

        self.gateway.cancel_order(req)

    def get_account(self) -> list[AccountData]:
        """Get account data.

        Returns:
            List of account data
        """
        if not self.main_engine:
            raise ConnectionError("Main engine not initialized")

        return self.main_engine.get_all_accounts()

    def get_position(self) -> list[PositionData]:
        """Get position data.

        Returns:
            List of position data
        """
        if not self.main_engine:
            raise ConnectionError("Main engine not initialized")

        return self.main_engine.get_all_positions()

    def get_order(self) -> list[OrderData]:
        """Get order data.

        Returns:
            List of order data
        """
        if not self.main_engine:
            raise ConnectionError("Main engine not initialized")

        return self.main_engine.get_all_orders()

    def get_trade(self) -> list[TradeData]:
        """Get trade data.

        Returns:
            List of trade data
        """
        if not self.main_engine:
            raise ConnectionError("Main engine not initialized")

        return self.main_engine.get_all_trades()

    def get_contract(self, vt_symbol: str) -> ContractData | None:
        """Get contract data.

        Args:
            vt_symbol: VN.py symbol format

        Returns:
            Contract data or None
        """
        if not self.main_engine:
            raise ConnectionError("Main engine not initialized")

        return self.main_engine.get_contract(vt_symbol)

    def is_connected(self) -> bool:
        """Check if connected to IB Gateway.

        Returns:
            True if connected, False otherwise
        """
        return bool(self.connected)


class GatewayManager:
    """Manages IB Gateway connection lifecycle."""

    def __init__(self) -> None:
        """Initialize gateway manager."""
        self.connection: IBGatewayConnection | None = None

    async def start(self) -> None:
        """Start IB Gateway connection.

        Raises:
            ConnectionError: If connection fails
        """
        self.connection = IBGatewayConnection()
        await self.connection.connect()

    async def stop(self) -> None:
        """Stop IB Gateway connection."""
        if self.connection:
            await self.connection.disconnect()
            self.connection = None

    def get_connection(self) -> IBGatewayConnection | None:
        """Get active connection.

        Returns:
            IBGatewayConnection instance or None
        """
        return self.connection


gateway_manager = GatewayManager()
