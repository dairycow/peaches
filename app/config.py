"""Configuration management using Pydantic Settings v2."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    path: str = Field(
        default="/home/hf/cooltrader/data/cooltrader.db", description="SQLite database path"
    )


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    file: str = Field(default="/app/logs/bot.log", description="Log file path")
    rotation: str = Field(default="100 MB", description="Log rotation size")
    retention: str = Field(default="7 days", description="Log retention period")
    json_format: bool = Field(default=True, description="Use JSON log format")


class HealthCheckConfig(BaseSettings):
    """Health check configuration."""

    unhealthy_threshold: int = Field(
        default=3, ge=1, description="Consecutive failures before unhealthy"
    )


class ASXScannerConfig(BaseSettings):
    """ASX scanner configuration."""

    url: str = Field(
        default="https://www.asx.com.au/asx/v2/statistics/todayAnns.do",
        description="ASX announcements URL",
    )
    scan_schedule: str = Field(default="30 10 * * 1-5", description="Scan cron schedule (AEST)")
    announcement_gap_schedule: str = Field(
        default="1 10 * * 1-5",
        description="Announcement gap scan cron schedule (AEST)",
    )
    timeout: int = Field(default=10, ge=1, description="Request timeout in seconds")


class DiscordConfig(BaseSettings):
    """Discord webhook configuration."""

    enabled: bool = Field(default=True, description="Enable Discord notifications")
    webhook_url: str = Field(default="", description="Discord webhook URL")
    username: str = Field(default="peaches-bot", description="Discord bot username")


class NotificationsConfig(BaseSettings):
    """Notifications configuration."""

    discord: DiscordConfig = Field(default_factory=DiscordConfig)


class ScannerServiceConfig(BaseSettings):
    """Scanner service configuration for ASX announcements."""

    enabled: bool = Field(default=True, description="Enable scanner service")
    asx: ASXScannerConfig = Field(default_factory=ASXScannerConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)


class AnnouncementGapStrategyConfig(BaseSettings):
    """Announcement gap strategy configuration."""

    min_price: float = Field(default=0.20, ge=0.01, description="Minimum stock price")
    min_gap_pct: float = Field(default=0.0, ge=0, description="Minimum gap percentage")
    lookback_months: int = Field(default=6, ge=1, le=24, description="Lookback period for high")


class Config(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    health: HealthCheckConfig = Field(default_factory=HealthCheckConfig)
    scanners: ScannerServiceConfig = Field(default_factory=ScannerServiceConfig)
    announcement_gap_strategy: AnnouncementGapStrategyConfig = Field(
        default_factory=AnnouncementGapStrategyConfig
    )

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls()


config: Config = Config.load()
