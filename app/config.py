"""Configuration management using Pydantic Settings v2."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from ruamel.yaml import YAML


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

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Log level"
    )
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
    tws_userid: str = Field(default="", description="IBKR username for authentication")


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

    @model_validator(mode="after")
    def make_paths_absolute(self) -> "HistoricalDataConfig":
        """Ensure all paths are absolute."""
        self.csv_dir = str(Path(self.csv_dir).absolute())
        self.db_path = str(Path(self.db_path).absolute())
        return self


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

    @model_validator(mode="after")
    def make_path_absolute(self) -> "AnalysisConfig":
        """Ensure output path is absolute."""
        self.output_dir = str(Path(self.output_dir).absolute())
        return self


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


class Config(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        case_sensitive=False,
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

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "Config":
        """Load configuration from YAML file with environment variable overrides.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Config instance with loaded settings

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML parsing fails
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        yaml = YAML()
        with open(config_path) as f:
            config_dict = yaml.load(f) or {}

        config_dict = cls._normalize_keys(config_dict)

        database_data = config_dict.pop("database", {})
        logging_data = config_dict.pop("logging", {})
        gateway_data = config_dict.pop("gateway", {})
        health_data = config_dict.pop("health", {})
        historical_data_data = config_dict.pop("historical_data", {})
        cooltrader_data = config_dict.pop("cooltrader", {})
        analysis_data = config_dict.pop("analysis", {})
        scanners_data = config_dict.pop("scanners", {})
        scanner_data = config_dict.pop("scanner", {})

        database_config = DatabaseConfig(**database_data)
        logging_config = LoggingConfig(**logging_data)
        gateway_config = IBGatewayConfig(**gateway_data)
        health_config = HealthCheckConfig(**health_data)
        historical_data_config = HistoricalDataConfig(**historical_data_data)
        cooltrader_config = CoolTraderConfig(**cooltrader_data)
        analysis_config = AnalysisConfig(**analysis_data)
        scanners_config = ScannerServiceConfig(**scanners_data)
        scanner_config = GapScannerConfig(**scanner_data)

        return cls(
            database=database_config,
            logging=logging_config,
            gateway=gateway_config,
            health=health_config,
            historical_data=historical_data_config,
            cooltrader=cooltrader_config,
            analysis=analysis_config,
            scanners=scanners_config,
            scanner=scanner_config,
        )

    @staticmethod
    def _normalize_keys(data: dict[str, Any]) -> dict[str, Any]:
        """Convert hyphenated keys to underscored for Python compatibility.

        Args:
            data: Dictionary with possibly hyphenated keys

        Returns:
            Dictionary with normalized keys
        """
        normalized = {}
        for key, value in data.items():
            new_key = key.replace("-", "_")
            if isinstance(value, dict):
                normalized[new_key] = Config._normalize_keys(value)
            else:
                normalized[new_key] = value
        return normalized


def load_config(config_path: str | Path = "/app/config/settings.yaml") -> Config:
    """Load application configuration.

    Args:
        config_path: Path to configuration file

    Returns:
        Config instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    try:
        return Config.from_yaml(config_path)
    except FileNotFoundError:
        return Config()


config: Config = load_config()
