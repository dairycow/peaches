"""Gateway management service."""

import asyncio

from loguru import logger

from app.config import config
from app.gateway import gateway_manager
from app.services.health_service import health_checker


class GatewayService:
    """Service for managing gateway connections."""

    @staticmethod
    async def start() -> None:
        """Initialize IB Gateway connection."""
        logger.info("Initializing IB Gateway connection...")

        try:
            await gateway_manager.start()
            health_checker.set_gateway_status(True)
            logger.info("IB Gateway connection established")
        except Exception as e:
            health_checker.set_gateway_status(False)
            logger.error(f"Failed to initialize IB Gateway: {e}")
            raise

    @staticmethod
    async def stop() -> None:
        """Stop IB Gateway connection."""
        await gateway_manager.stop()

    @staticmethod
    async def health_check_loop() -> None:
        """Run periodic health checks."""
        while True:
            try:
                connection = gateway_manager.get_connection()

                if connection and connection.is_connected():
                    health_checker.set_gateway_status(True)
                else:
                    health_checker.set_gateway_status(False)
                    if config.gateway.auto_reconnect:
                        logger.warning("Gateway disconnected, attempting to reconnect...")
                        try:
                            await gateway_manager.start()
                        except Exception as e:
                            logger.error(f"Reconnection failed: {e}")

                await asyncio.sleep(config.health.interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(config.health.interval_seconds)


gateway_service = GatewayService()
