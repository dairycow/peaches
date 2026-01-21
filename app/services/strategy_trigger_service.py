"""Strategy trigger service for triggering trading strategies."""

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    pass


class StrategyTriggerService:
    """Service for triggering trading strategies based on announcements."""

    def __init__(self, enabled: bool, strategy_names: list[str]) -> None:
        """Initialize strategy trigger service.

        Args:
            enabled: Whether strategy triggering is enabled
            strategy_names: List of strategy module names to trigger
        """
        self.enabled = enabled
        self.strategy_names = strategy_names

    async def trigger_strategies(self, ticker: str, headline: str) -> None:
        """Trigger trading strategies for announcement.

        Args:
            ticker: Ticker symbol
            headline: Announcement headline
        """
        if not self.enabled:
            logger.info(f"Strategy triggering disabled, skipping {ticker}")
            return

        from app.strategies import get_strategy

        for strategy_name in self.strategy_names:
            try:
                strategy_module = get_strategy(strategy_name)

                logger.info(f"Triggering strategy '{strategy_name}' for ticker {ticker}")
                logger.info(f"  Headline: {headline}")

                if hasattr(strategy_module, "on_announcement"):
                    strategy_module.on_announcement(ticker, headline)
                else:
                    logger.debug(f"Strategy '{strategy_name}' has no on_announcement method")

            except ImportError as e:
                logger.error(f"Strategy '{strategy_name}' not found: {e}")
            except Exception as e:
                logger.error(f"Error triggering strategy '{strategy_name}' for {ticker}: {e}")


strategy_trigger_service: StrategyTriggerService | None = None


def get_strategy_trigger_service(
    enabled: bool, strategy_names: list[str]
) -> StrategyTriggerService:
    """Get or create strategy trigger service singleton.

    Args:
        enabled: Whether strategy triggering is enabled
        strategy_names: List of strategy module names to trigger

    Returns:
        StrategyTriggerService instance
    """
    global strategy_trigger_service
    if strategy_trigger_service is None:
        strategy_trigger_service = StrategyTriggerService(enabled, strategy_names)
    return strategy_trigger_service
