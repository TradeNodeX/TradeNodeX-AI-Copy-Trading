CREATE TABLE IF NOT EXISTS follower_accounts (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    environment VARCHAR(16) NOT NULL DEFAULT 'TESTNET',
    account_group VARCHAR(64) NOT NULL DEFAULT 'default',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    scale_factor NUMERIC(20, 8) NOT NULL DEFAULT 1.0,
    exact_copy_mode BOOLEAN NOT NULL DEFAULT TRUE,
    leverage INTEGER,
    margin_mode VARCHAR(16) NOT NULL DEFAULT 'ISOLATED',
    hedge_mode BOOLEAN NOT NULL DEFAULT FALSE,
    validation_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    validation_message TEXT,
    last_validated_at TIMESTAMP,
    api_key_ciphertext TEXT,
    api_secret_ciphertext TEXT,
    kms_key_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS signal_sources (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(140) NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    environment VARCHAR(16) NOT NULL DEFAULT 'TESTNET',
    source_account VARCHAR(128) NOT NULL,
    description TEXT,
    pairs_scope VARCHAR(64) NOT NULL DEFAULT 'ALL',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    default_copy_mode VARCHAR(16) NOT NULL DEFAULT 'EXACT',
    default_scale_factor NUMERIC(20, 8) NOT NULL DEFAULT 1.0,
    default_leverage INTEGER,
    margin_mode VARCHAR(16) NOT NULL DEFAULT 'ISOLATED',
    hedge_mode BOOLEAN NOT NULL DEFAULT FALSE,
    broadcast_trade_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    api_key_ciphertext TEXT,
    api_secret_ciphertext TEXT,
    kms_key_id VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    UNIQUE(exchange, environment, source_account)
);

CREATE TABLE IF NOT EXISTS copy_trades (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(140) NOT NULL,
    signal_source_id VARCHAR(36) NOT NULL REFERENCES signal_sources(id) ON DELETE CASCADE,
    follower_account_id VARCHAR(36) NOT NULL REFERENCES follower_accounts(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    copy_mode VARCHAR(16) NOT NULL DEFAULT 'EXACT',
    scale_factor NUMERIC(20, 8) NOT NULL DEFAULT 1.0,
    override_leverage INTEGER,
    override_margin_mode VARCHAR(16),
    override_hedge_mode BOOLEAN,
    command_template TEXT,
    notes TEXT,
    validation_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    validation_message TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    UNIQUE(signal_source_id, follower_account_id)
);

CREATE TABLE IF NOT EXISTS account_symbol_rules (
    id VARCHAR(36) PRIMARY KEY,
    follower_account_id VARCHAR(36) NOT NULL REFERENCES follower_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(32) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    scale_factor NUMERIC(20, 8),
    max_leverage INTEGER,
    max_notional NUMERIC(24, 8),
    min_notional_override NUMERIC(24, 8),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    UNIQUE(follower_account_id, symbol)
);

CREATE TABLE IF NOT EXISTS master_events (
    id VARCHAR(36) PRIMARY KEY,
    signal_source_id VARCHAR(36) REFERENCES signal_sources(id) ON DELETE SET NULL,
    source_exchange VARCHAR(32) NOT NULL,
    source_account VARCHAR(128) NOT NULL,
    source_order_or_fill_id VARCHAR(128) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    previous_position_qty NUMERIC(24, 8) NOT NULL,
    current_position_qty NUMERIC(24, 8) NOT NULL,
    price NUMERIC(24, 8),
    event_time TIMESTAMP NOT NULL,
    payload JSON NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS normalized_signals (
    id VARCHAR(36) PRIMARY KEY,
    signal_source_id VARCHAR(36) NOT NULL REFERENCES signal_sources(id) ON DELETE CASCADE,
    master_event_id VARCHAR(36) NOT NULL REFERENCES master_events(id) ON DELETE CASCADE,
    source_exchange VARCHAR(32) NOT NULL,
    source_account VARCHAR(128) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    action VARCHAR(64) NOT NULL,
    target_side VARCHAR(32) NOT NULL,
    target_quantity NUMERIC(24, 8) NOT NULL,
    delta_quantity NUMERIC(24, 8) NOT NULL,
    status VARCHAR(32) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_tasks (
    id VARCHAR(36) PRIMARY KEY,
    signal_id VARCHAR(36) NOT NULL REFERENCES normalized_signals(id) ON DELETE CASCADE,
    signal_source_id VARCHAR(36) NOT NULL REFERENCES signal_sources(id) ON DELETE CASCADE,
    copy_trade_id VARCHAR(36) REFERENCES copy_trades(id) ON DELETE SET NULL,
    follower_account_id VARCHAR(36) NOT NULL REFERENCES follower_accounts(id) ON DELETE CASCADE,
    exchange VARCHAR(32) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    action VARCHAR(64) NOT NULL,
    target_side VARCHAR(32) NOT NULL,
    target_quantity NUMERIC(24, 8) NOT NULL,
    delta_quantity NUMERIC(24, 8) NOT NULL,
    copy_mode VARCHAR(16) NOT NULL DEFAULT 'EXACT',
    reduce_only BOOLEAN NOT NULL DEFAULT FALSE,
    queue_name VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,
    message_group VARCHAR(255) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_attempts (
    id VARCHAR(36) PRIMARY KEY,
    execution_task_id VARCHAR(36) NOT NULL REFERENCES execution_tasks(id) ON DELETE CASCADE,
    attempt_no INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL,
    request_payload JSON NOT NULL,
    response_payload JSON,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS position_snapshots (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    quantity NUMERIC(24, 8) NOT NULL,
    entry_price NUMERIC(24, 8),
    leverage INTEGER,
    source VARCHAR(32) NOT NULL,
    captured_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS reconciliation_results (
    id VARCHAR(36) PRIMARY KEY,
    signal_id VARCHAR(36) NOT NULL REFERENCES normalized_signals(id) ON DELETE CASCADE,
    follower_account_id VARCHAR(36) NOT NULL REFERENCES follower_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(32) NOT NULL,
    expected_quantity NUMERIC(24, 8) NOT NULL,
    actual_quantity NUMERIC(24, 8) NOT NULL,
    delta_quantity NUMERIC(24, 8) NOT NULL,
    status VARCHAR(32) NOT NULL,
    action_taken VARCHAR(64),
    details JSON NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS command_presets (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(140) NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    environment VARCHAR(16) NOT NULL DEFAULT 'TESTNET',
    account_id VARCHAR(36) REFERENCES follower_accounts(id) ON DELETE SET NULL,
    signal_source_id VARCHAR(36) REFERENCES signal_sources(id) ON DELETE SET NULL,
    payload JSON NOT NULL,
    raw_command TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS trade_logs (
    id VARCHAR(36) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    log_type VARCHAR(32) NOT NULL,
    log_key VARCHAR(64) NOT NULL,
    pnl NUMERIC(24, 8),
    message TEXT NOT NULL,
    details JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS operator_actions (
    id VARCHAR(36) PRIMARY KEY,
    operator VARCHAR(128) NOT NULL,
    action VARCHAR(64) NOT NULL,
    target_type VARCHAR(64) NOT NULL,
    target_id VARCHAR(64) NOT NULL,
    details JSON NOT NULL,
    created_at TIMESTAMP NOT NULL
);
