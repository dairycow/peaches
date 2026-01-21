"""Notification service for sending alerts via Discord webhook."""

from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    pass


class NotificationService:
    """Service for sending Discord notifications."""

    def __init__(self, webhook_url: str, username: str, enabled: bool) -> None:
        """Initialize notification service.

        Args:
            webhook_url: Discord webhook URL
            username: Discord bot username
            enabled: Whether notifications are enabled
        """
        self.webhook_url = webhook_url
        self.username = username
        self.enabled = enabled

    async def send_discord_webhook(
        self,
        ticker: str,
        headline: str,
        timestamp: str,
    ) -> None:
        """Send Discord webhook notification.

        Args:
            ticker: Ticker symbol
            headline: Announcement headline
            timestamp: Timestamp of announcement
        """
        if not self.enabled:
            logger.debug(f"Discord notifications disabled, skipping {ticker}")
            return

        import httpx

        payload = {
            "content": f"**{ticker}**: {headline}\n*{timestamp}*",
            "username": self.username,
        }

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(self.webhook_url, json=payload)
            logger.info(f"Discord notification sent for {ticker}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")


notification_service: NotificationService | None = None


def get_notification_service(webhook_url: str, username: str, enabled: bool) -> NotificationService:
    """Get or create notification service singleton.

    Args:
        webhook_url: Discord webhook URL
        username: Discord bot username
        enabled: Whether notifications are enabled

    Returns:
        NotificationService instance
    """
    global notification_service
    if notification_service is None:
        notification_service = NotificationService(webhook_url, username, enabled)
    return notification_service
