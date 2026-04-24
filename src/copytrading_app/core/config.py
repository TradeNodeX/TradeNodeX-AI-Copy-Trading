from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    service_name: str = "tradenodex-control-center"
    database_url: str = "sqlite+aiosqlite:///./copytrading.db"
    db_echo: bool = False
    binance_base_url: str = "https://testnet.binancefuture.com"
    binance_ws_base_url: str = "wss://stream.binancefuture.com"
    bybit_base_url: str = "https://api-testnet.bybit.com"
    bybit_ws_base_url: str = "wss://stream-testnet.bybit.com"
    okx_base_url: str = "https://www.okx.com"
    okx_ws_base_url: str = "wss://ws.okx.com:8443"
    okx_demo_ws_base_url: str = "wss://wspap.okx.com:8443"
    okx_demo_header: str = "1"
    coinbase_base_url: str = "https://api.coinbase.com"
    coinbase_sandbox_base_url: str = "https://api-sandbox.coinbase.com"
    coinbase_ws_base_url: str = "wss://advanced-trade-ws.coinbase.com"
    coinbase_sandbox_ws_base_url: str = "wss://advanced-trade-ws-sandbox.coinbase.com"
    kraken_base_url: str = "https://futures.kraken.com"
    kraken_demo_base_url: str = "https://demo-futures.kraken.com"
    kraken_ws_base_url: str = "wss://futures.kraken.com/ws/v1"
    kraken_demo_ws_base_url: str = "wss://demo-futures.kraken.com/ws/v1"
    bitmex_base_url: str = "https://www.bitmex.com"
    bitmex_testnet_base_url: str = "https://testnet.bitmex.com"
    bitmex_ws_base_url: str = "wss://www.bitmex.com/realtime"
    bitmex_testnet_ws_base_url: str = "wss://testnet.bitmex.com/realtime"
    gateio_base_url: str = "https://fx-api.gateio.ws"
    gateio_testnet_base_url: str = "https://fx-api-testnet.gateio.ws"
    gateio_ws_base_url: str = "wss://fx-ws.gateio.ws/v4/ws/usdt"
    gateio_testnet_ws_base_url: str = "wss://fx-ws-testnet.gateio.ws/v4/ws/usdt"
    api_timeout_seconds: float = 10.0
    default_recv_window_ms: int = 5000
    aws_region: str = "ap-northeast-1"
    queue_backend: str = "memory"
    sqs_queue_url_normal: str | None = None
    sqs_queue_url_risk: str | None = None
    sqs_queue_url_recovery: str | None = None
    redis_url: str = "redis://localhost:6379/0"
    redis_prefix: str = "copytrading"
    kms_backend: str = "local"
    kms_key_id: str | None = None
    default_environment: str = "TESTNET"
    serve_frontend: bool = True
    default_queue_visibility_seconds: int = 30
    reconciler_tolerance: float = Field(default=0.000001, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
