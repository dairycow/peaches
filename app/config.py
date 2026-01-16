"""Configuration management using Pydantic Settings v2."""

from pathlib import Path
from typing import Literal

from pydantic import Field
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


class Config(BaseSettings):
    """Main application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    gateway: IBGatewayConfig = Field(default_factory=IBGatewayConfig)
    health: HealthCheckConfig = Field(default_factory=HealthCheckConfig)

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

        database_config = DatabaseConfig(**database_data)
        logging_config = LoggingConfig(**logging_data)
        gateway_config = IBGatewayConfig(**gateway_data)
        health_config = HealthCheckConfig(**health_data)

        return cls(
            database=database_config,
            logging=logging_config,
            gateway=gateway_config,
            health=health_config,
        )

    @staticmethod
    def _normalize_keys(data: dict) -> dict:
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
