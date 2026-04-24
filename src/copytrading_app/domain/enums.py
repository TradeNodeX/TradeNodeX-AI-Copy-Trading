from enum import StrEnum


class Exchange(StrEnum):
    BINANCE = "BINANCE"
    BYBIT = "BYBIT"
    OKX = "OKX"
    COINBASE = "COINBASE"
    KRAKEN = "KRAKEN"
    BITMEX = "BITMEX"
    GATEIO = "GATEIO"


class RuntimeEnvironment(StrEnum):
    TESTNET = "TESTNET"
    MAINNET = "MAINNET"
    DEMO = "DEMO"


class FollowerStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class SignalSourceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


class CopyTradeStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class ValidationStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class SignalAction(StrEnum):
    OPEN = "OPEN"
    INCREASE = "INCREASE"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    FLIP = "FLIP"
    SYNC_TO_TARGET_POSITION = "SYNC_TO_TARGET_POSITION"


class SignalStatus(StrEnum):
    RECEIVED = "RECEIVED"
    NORMALIZED = "NORMALIZED"
    PLANNED = "PLANNED"
    DISPATCHED = "DISPATCHED"
    ACKED = "ACKED"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RECONCILED = "RECONCILED"


class PositionSide(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


class QueueName(StrEnum):
    NORMAL_EXEC = "normal-exec"
    RISK_PRIORITY = "risk-priority"
    RECOVERY = "recovery"


class AttemptStatus(StrEnum):
    PENDING = "PENDING"
    ACKED = "ACKED"
    FAILED = "FAILED"
    FILLED = "FILLED"


class ReconciliationStatus(StrEnum):
    MATCHED = "MATCHED"
    OUT_OF_SYNC = "OUT_OF_SYNC"
    REPAIR_ENQUEUED = "REPAIR_ENQUEUED"


class MarginMode(StrEnum):
    ISOLATED = "ISOLATED"
    CROSS = "CROSS"


class CopyMode(StrEnum):
    EXACT = "EXACT"
    SCALE = "SCALE"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"


class BuilderAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    CANCEL_ORDERS = "CANCEL_ORDERS"
    CLOSE_POSITION = "CLOSE_POSITION"


class QuantityMode(StrEnum):
    ABSOLUTE = "ABSOLUTE"
    PERCENT_AVAILABLE = "PERCENT_AVAILABLE"
    PERCENT_WALLET = "PERCENT_WALLET"
    RISK_PERCENT = "RISK_PERCENT"
    COPY_TRADER = "COPY_TRADER"


class LogType(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    EXECUTION = "EXECUTION"
    SIGNAL = "SIGNAL"
    RECONCILE = "RECONCILE"
    MANUAL = "MANUAL"
