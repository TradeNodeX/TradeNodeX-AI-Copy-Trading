export type View =
  | "SIGNALS"
  | "COPY_TRADES"
  | "MANAGE_SIGNALS"
  | "EXECUTION_STUDIO"
  | "TRADE_LOGS"
  | "POSITIONS";

export type Tone = "neutral" | "good" | "danger" | "warning";

export type ValidationStatus = "PENDING" | "VERIFIED" | "FAILED";
export type SignalSourceStatus = "ACTIVE" | "PAUSED" | "FAILED";
export type FollowerStatus = "ACTIVE" | "PAUSED" | "FAILED";
export type CopyTradeStatus = "ACTIVE" | "PAUSED" | "FAILED";
export type CopyMode = "EXACT" | "SCALE";
export type SignalStatus =
  | "RECEIVED"
  | "NORMALIZED"
  | "PLANNED"
  | "DISPATCHED"
  | "ACKED"
  | "FILLED"
  | "PARTIAL"
  | "FAILED"
  | "SKIPPED"
  | "RECONCILED";
export type BuilderAction = "BUY" | "SELL" | "CANCEL_ORDERS" | "CLOSE_POSITION";
export type OrderType = "MARKET" | "LIMIT" | "STOP_MARKET";
export type RuntimeEnvironment = "MAINNET" | "TESTNET" | "DEMO";
export type Exchange =
  | "BINANCE"
  | "BYBIT"
  | "OKX"
  | "COINBASE"
  | "KRAKEN"
  | "BITMEX"
  | "GATEIO";

export interface DashboardMetric {
  label: string;
  value: string | number;
  tone: Tone;
  note?: string | null;
}

export interface FxMeta {
  display_currency: string;
  source_currency: string;
  conversion_source: string;
  converted: boolean;
  updated_at: string | null;
  available_rates: string[];
}

export interface EquitySummary {
  total_notional: string;
  long_exposure: string;
  short_exposure: string;
  stale_snapshots: number;
  total_unrealized_pnl: string;
}

export interface WorkerStatus {
  status: string;
  updated_at: string | null;
  age_seconds: number | null;
}

export interface SignalSource {
  id: string;
  name: string;
  exchange: Exchange;
  environment: RuntimeEnvironment;
  source_account: string;
  description: string | null;
  pairs_scope: string;
  status: SignalSourceStatus;
  default_copy_mode: CopyMode;
  default_scale_factor: string;
  default_leverage: number | null;
  margin_mode: string;
  hedge_mode: boolean;
  broadcast_trade_enabled: boolean;
  follower_count: number;
  invitation_count: number;
  follower_names: string[];
  validation_status: ValidationStatus;
  validation_message: string | null;
  credential_status: ValidationStatus;
  permission_status: ValidationStatus;
  connectivity_status: ValidationStatus;
  trading_ready_status: ValidationStatus;
  validation_reasons: string[];
  last_validated_at: string | null;
  stream_status: string;
  listener_status: string;
  last_stream_event_at: string | null;
}

export interface Follower {
  id: string;
  name: string;
  exchange: Exchange;
  environment: RuntimeEnvironment;
  account_group: string;
  status: FollowerStatus;
  scale_factor: string;
  exact_copy_mode: boolean;
  leverage: number | null;
  margin_mode: string;
  hedge_mode: boolean;
  validation_status: ValidationStatus;
  validation_message: string | null;
  credential_status: ValidationStatus;
  permission_status: ValidationStatus;
  connectivity_status: ValidationStatus;
  trading_ready_status: ValidationStatus;
  validation_reasons: string[];
  last_validated_at: string | null;
}

export interface CopyTrade {
  id: string;
  name: string;
  signal_source_id: string;
  signal_name: string;
  follower_account_id: string;
  follower_name: string;
  exchange: Exchange;
  status: CopyTradeStatus;
  enabled: boolean;
  copy_mode: CopyMode;
  scale_factor: string;
  override_leverage: number | null;
  override_margin_mode: string | null;
  override_hedge_mode: boolean | null;
  command_template: string | null;
  notes: string | null;
  validation_status: ValidationStatus;
  validation_message: string | null;
  validation_reasons: string[];
}

export interface TradeLog {
  id: string;
  timestamp: string;
  exchange: Exchange;
  log_type: string;
  log_key: string;
  pnl: string | null;
  message: string;
  details: Record<string, unknown>;
  linked_task_id: string | null;
  linked_signal_id: string | null;
  linked_follower_id: string | null;
  linked_follower_name: string | null;
  linked_copy_trade_id: string | null;
  exchange_response: Record<string, unknown> | null;
}

export interface ExecutionAttempt {
  id: string;
  attempt_no: number;
  status: string;
  request_payload: Record<string, unknown>;
  response_payload: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ExecutionTask {
  id: string;
  signal_id: string;
  signal_source_id: string;
  copy_trade_id: string | null;
  follower_account_id: string;
  exchange: Exchange;
  symbol: string;
  action: string;
  target_side: string;
  target_quantity: string;
  delta_quantity: string;
  queue_name: string;
  status: SignalStatus;
  copy_mode: CopyMode;
  reduce_only: boolean;
  error_message: string | null;
  follower_name: string | null;
  signal_name: string | null;
  latest_attempt_status: string | null;
  latest_attempt_error: string | null;
  latest_exchange_response: Record<string, unknown> | null;
  queue_latency_ms: number | null;
  exchange_stage: string | null;
  attempts: ExecutionAttempt[];
}

export interface ExecutionTimelineItem {
  id: string;
  timestamp: string;
  source_type: string;
  level: string;
  title: string;
  message: string;
  payload: Record<string, unknown>;
}

export interface ExecutionAudit {
  task: ExecutionTask;
  related_logs: TradeLog[];
  timeline: ExecutionTimelineItem[];
}

export interface PositionSnapshot {
  id: string;
  account_id: string;
  exchange: Exchange;
  symbol: string;
  quantity: string;
  entry_price: string | null;
  mark_price: string | null;
  leverage: number | null;
  margin_mode: string | null;
  source: string;
  follower_name: string | null;
  unrealized_pnl: string | null;
  notional_exposure: string | null;
  display_value: string | null;
  freshness: string;
  captured_at: string;
}

export interface CommandPreset {
  id: string;
  name: string;
  exchange: Exchange;
  environment: RuntimeEnvironment;
  account_id: string | null;
  signal_source_id: string | null;
  payload: Record<string, unknown>;
  raw_command: string;
  created_at: string;
  updated_at: string;
}

export interface DashboardResponse {
  signal_sources: SignalSource[];
  copy_trades: CopyTrade[];
  followers: Follower[];
  logs: TradeLog[];
  recent_executions: ExecutionTask[];
  command_presets: CommandPreset[];
  runtime_metrics: DashboardMetric[];
  performance_metrics: DashboardMetric[];
  fx_meta: FxMeta | null;
  equity_summary: EquitySummary | null;
  worker_status: WorkerStatus | null;
}

export interface TradeLogListResponse {
  items: TradeLog[];
  total: number;
  page: number;
  limit: number;
  page_count: number;
}

export interface ValidationResult {
  ok: boolean;
  message: string | null;
}

export interface ManualExecutionResponse {
  accepted: boolean;
  preset_id: string | null;
  result: Record<string, unknown>;
}

export interface Instrument {
  [key: string]: unknown;
}

export interface WebsocketSnapshot {
  type: "snapshot" | "pong";
  counts?: {
    signals: number;
    copy_trades: number;
    followers: number;
    logs: number;
  };
  logs?: TradeLog[];
  executions?: ExecutionTask[];
  fx_meta?: FxMeta;
  equity_summary?: EquitySummary;
  worker_status?: WorkerStatus;
}
