"""Configuration management using Pydantic Settings v2."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    path: str = Field(default="/app/data/trading.db", description="SQLite database path")
    backup_enabled: bool = Field(default=True, description="Enable automatic backups")
    backup_interval_hours: int = Field(default=24, ge=1, description="Backup interval in hours")
    backup_retention_days: int = Field(
        default=30, ge=1, description="Backup retention period in days"
    )


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    file: str = Field(default="/app/logs/bot.log", description="Log file path")
    rotation: str = Field(default="100 MB", description="Log rotation size")
    retention: str = Field(default="7 days", description="Log retention period")
    json_format: bool = Field(default=True, description="Use JSON log format")


class IBGatewayConfig(BaseSettings):
    """IB Gateway connection configuration."""

    host: str = Field(default="ib-gateway", description="IB Gateway host")
    port: int = Field(default=4004, ge=1, le=65535, description="IB Gateway port")
    client_id: int = Field(default=1, ge=1, description="Client ID for IB API")
    connect_timeout: int = Field(default=30, ge=1, description="Connection timeout in seconds")
    auto_reconnect: bool = Field(default=True, description="Enable auto-reconnect")
    reconnect_interval: int = Field(default=5, ge=1, description="Reconnect interval in seconds")
    max_reconnect_attempts: int = Field(default=10, ge=1, description="Maximum reconnect attempts")


class HealthCheckConfig(BaseSettings):
    """Health check configuration."""

    enabled: bool = Field(default=True, description="Enable health checks")
    interval_seconds: int = Field(default=30, ge=1, description="Health check interval")
    gateway_timeout: int = Field(default=5, ge=1, description="Gateway ping timeout")
    unhealthy_threshold: int = Field(
        default=3, ge=1, description="Consecutive failures before unhealthy"
    )


class HistoricalDataConfig(BaseSettings):
    """Historical data configuration."""

    csv_dir: str = Field(default="/app/data/raw/cooltrader", description="CSV data directory")
    db_path: str = Field(
        default="/app/data/historical.db", description="Historical data database path"
    )
    import_enabled: bool = Field(default=True, description="Enable data import")


class CoolTraderConfig(BaseSettings):
    """CoolTrader data provider configuration."""

    username: str = Field(default="", description="CoolTrader username")
    password: str = Field(default="", description="CoolTrader password")
    base_url: str = Field(
        default="https://data.cooltrader.com.au", description="CoolTrader API base URL"
    )
    download_schedule: str = Field(default="0 10 * * *", description="Download cron schedule")
    import_schedule: str = Field(default="5 10 * * *", description="Import cron schedule")


class AnalysisConfig(BaseSettings):
    """Backtesting analysis configuration."""

    output_dir: str = Field(default="/app/data/analysis", description="Analysis output directory")
    default_capital: float = Field(default=1_000_000, description="Default backtest capital")
    commission_rate: float = Field(default=0.001, description="Commission rate")
    slippage: float = Field(default=0.02, description="Slippage percentage (2%)")
    fixed_commission: float = Field(default=6.6, description="Fixed commission per trade ($6.60)")


class ASXScannerConfig(BaseSettings):
    """ASX scanner configuration."""

    url: str = Field(
        default="https://www.asx.com.au/asx/v2/statistics/todayAnns.do",
        description="ASX announcements URL",
    )
    scan_schedule: str = Field(default="30 10 * * 1-5", description="Scan cron schedule (AEST)")
    timeout: int = Field(default=10, ge=1, description="Request timeout in seconds")
    exclude_tickers: list[str] = Field(default_factory=list, description="Tickers to exclude")
    min_ticker_length: int = Field(default=3, ge=1, le=6, description="Minimum ticker length")
    max_ticker_length: int = Field(default=6, ge=1, le=6, description="Maximum ticker length")


class DiscordConfig(BaseSettings):
    """Discord webhook configuration."""

    enabled: bool = Field(default=True, description="Enable Discord notifications")
    webhook_url: str = Field(default="", description="Discord webhook URL")
    username: str = Field(default="peaches-bot", description="Discord bot username")


class NotificationsConfig(BaseSettings):
    """Notifications configuration."""

    discord: DiscordConfig = Field(default_factory=DiscordConfig)


class TriggerConfig(BaseSettings):
    """Strategy trigger configuration."""

    enabled: bool = Field(default=True, description="Enable strategy triggering")
    strategies: list[str] = Field(default_factory=list, description="Strategies to trigger")


class ScannerServiceConfig(BaseSettings):
    """Scanner service configuration for ASX announcements."""

    enabled: bool = Field(default=True, description="Enable scanner service")
    asx: ASXScannerConfig = Field(default_factory=ASXScannerConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    triggers: TriggerConfig = Field(default_factory=TriggerConfig)


class GapScannerConfig(BaseSettings):
    """Gap scanner configuration."""

    gap_threshold: float = Field(default=3.0, ge=0, le=50, description="Minimum gap percentage")
    min_price: float = Field(default=1.0, ge=0.01, description="Minimum stock price")
    min_volume: int = Field(default=100000, gt=0, description="Minimum daily volume")
    max_results: int = Field(default=50, ge=1, le=50, description="Maximum results to return")
    opening_range_time: str = Field(
        default="10:05", description="Opening range sample time (HH:MM)"
    )
    timezone: str = Field(default="Australia/Sydney", description="Scanner timezone")
    enable_scanner: bool = Field(default=False, description="Enable opening range scanner")


class AnnouncementGapStrategyConfig(BaseSettings):
    """Announcement gap strategy configuration."""

    min_price: float = Field(default=0.20, ge=0.01, description="Minimum stock price")
    min_gap_pct: float = Field(default=0.0, ge=0, description="Minimum gap percentage")
    lookback_months: int = Field(default=6, ge=1, le=24, description="Lookback period for high")
    opening_range_minutes: int = Field(default=5, ge=1, le=30, description="Opening range duration")
    position_size: int = Field(default=100, gt=0, description="Position size")
    max_positions: int = Field(default=10, gt=0, description="Maximum concurrent positions")
    exit_days: int = Field(default=3, ge=1, le=10, description="Exit after N days")
    enabled: bool = Field(default=False, description="Enable announcement gap strategy")


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
    gateway: IBGatewayConfig = Field(default_factory=IBGatewayConfig)
    health: HealthCheckConfig = Field(default_factory=HealthCheckConfig)
    historical_data: HistoricalDataConfig = Field(default_factory=HistoricalDataConfig)
    cooltrader: CoolTraderConfig = Field(default_factory=CoolTraderConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    scanners: ScannerServiceConfig = Field(default_factory=ScannerServiceConfig)
    scanner: GapScannerConfig = Field(default_factory=GapScannerConfig)
    announcement_gap_strategy: AnnouncementGapStrategyConfig = Field(
        default_factory=AnnouncementGapStrategyConfig
    )

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config instance
        """
        return cls()


config: Config = Config.load()
