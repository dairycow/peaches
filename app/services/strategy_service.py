"""Strategy management service."""

from loguru import logger
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctastrategy import CtaEngine

from app.strategies import DEFAULT_PARAMETERS, STRATEGY_NAME, VT_SYMBOL

cta_engine: CtaEngine | None = None


class StrategyService:
    """Service for managing trading strategies."""

    @staticmethod
    def initialize_cta_engine(main_engine: MainEngine, event_engine: EventEngine) -> CtaEngine:
        """Initialize CTA strategy engine.

        Args:
            main_engine: Main trading engine
            event_engine: Event engine

        Returns:
            CtaEngine instance
        """
        global cta_engine
        cta_engine = CtaEngine(main_engine, event_engine)
        cta_engine.init_engine()

        cta_engine.add_strategy(
            "ASXMomentumStrategy",
            STRATEGY_NAME,
            VT_SYMBOL,
            DEFAULT_PARAMETERS,
        )

        return cta_engine

    @staticmethod
    async def start() -> None:
        """Initialize trading strategies."""
        logger.info("Initializing strategies...")

        try:
            from app.external.ib import gateway_manager

            connection = gateway_manager.get_connection()
            if not connection or not connection.main_engine or not connection.event_engine:
                raise RuntimeError("Gateway connection not available")

            global cta_engine
            cta_engine = StrategyService.initialize_cta_engine(
                connection.main_engine, connection.event_engine
            )
            cta_engine.init_all_strategies()
            cta_engine.start_all_strategies()

            logger.info("Strategies initialized and started")

        except Exception as e:
            logger.error(f"Failed to initialize strategies: {e}")
            raise

    @staticmethod
    def stop() -> None:
        """Stop all strategies."""
        global cta_engine
        if cta_engine is not None:
            cta_engine.stop_all_strategies()


strategy_service = StrategyService()
