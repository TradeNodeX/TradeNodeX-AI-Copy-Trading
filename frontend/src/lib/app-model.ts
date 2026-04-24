import type { BuilderAction, CopyMode, DashboardResponse, ValidationStatus, View } from "../types";

export type Density = "standard" | "compact";
export type FontScale = "small" | "default" | "large";
export type MotionPref = "full" | "reduced";

export type SignalDraft = {
  id?: string;
  name: string;
  exchange: string;
  environment: string;
  source_account: string;
  description: string;
  pairs_scope: string;
  default_copy_mode: CopyMode;
  default_scale_factor: string;
  default_leverage: string;
  margin_mode: string;
  hedge_mode: boolean;
  broadcast_trade_enabled: boolean;
  api_key: string;
  api_secret: string;
  api_passphrase: string;
};

export type FollowerDraft = {
  id?: string;
  name: string;
  exchange: string;
  environment: string;
  account_group: string;
  scale_factor: string;
  exact_copy_mode: boolean;
  leverage: string;
  margin_mode: string;
  hedge_mode: boolean;
  api_key: string;
  api_secret: string;
  api_passphrase: string;
};

export type CopyTradeDraft = {
  id?: string;
  name: string;
  signal_source_id: string;
  follower_account_id: string;
  copy_mode: CopyMode;
  scale_factor: string;
  override_leverage: string;
  command_template: string;
  notes: string;
  enabled: boolean;
};

export type BuilderDraft = {
  name: string;
  exchange: string;
  environment: string;
  product_type: string;
  action: BuilderAction;
  symbol: string;
  order_type: string;
  quantity_mode: string;
  quantity_value: string;
  leverage: string;
  margin_mode: string;
  hedge_mode: boolean;
  broadcast_trade: boolean;
  create_copy_trade_signal: boolean;
  signal_source_id: string;
  account_id: string;
  limit_price: string;
  stop_price: string;
  stop_loss_percent: string;
  delay_seconds: string;
  use_dca: boolean;
  use_fixed_size: boolean;
  use_entire_balance: boolean;
  prevent_pyramiding: boolean;
  close_current_position: boolean;
  cancel_pending_orders: boolean;
  conditional_pyramiding: boolean;
  close_in_profit_only: boolean;
  cancel_all_orders: boolean;
  cancel_dca_orders: boolean;
  partial_close: boolean;
  close_by_limit_order: boolean;
  close_all: boolean;
  close_long: boolean;
  close_short: boolean;
  take_profit_steps: Array<{ id: string; amount: string; takeProfitPercent: string }>;
};

export const viewOrder: Array<{ id: View; label: string }> = [
  { id: "SIGNALS", label: "signals" },
  { id: "COPY_TRADES", label: "copyTrades" },
  { id: "MANAGE_SIGNALS", label: "apiRegistry" },
  { id: "EXECUTION_STUDIO", label: "studio" },
  { id: "TRADE_LOGS", label: "logs" },
  { id: "POSITIONS", label: "positions" }
];

export const exchanges = ["BINANCE", "BYBIT", "OKX", "COINBASE", "KRAKEN", "BITMEX", "GATEIO"];

export const exchangeEnvironments: Record<string, string[]> = {
  BINANCE: ["TESTNET", "MAINNET"],
  BYBIT: ["TESTNET", "MAINNET", "DEMO"],
  OKX: ["MAINNET", "DEMO"],
  COINBASE: ["MAINNET", "TESTNET"],
  KRAKEN: ["MAINNET", "DEMO"],
  BITMEX: ["TESTNET", "MAINNET"],
  GATEIO: ["TESTNET", "MAINNET"]
};

export function environmentsForExchange(exchange: string): string[] {
  return exchangeEnvironments[exchange] ?? ["TESTNET", "MAINNET"];
}

export function normalizeEnvironment(exchange: string, current: string): string {
  const allowed = environmentsForExchange(exchange);
  return allowed.includes(current) ? current : allowed[0];
}

export const initialSignalDraft = (): SignalDraft => ({
  name: "",
  exchange: "BINANCE",
  environment: "TESTNET",
  source_account: "",
  description: "",
  pairs_scope: "ALL",
  default_copy_mode: "EXACT",
  default_scale_factor: "1",
  default_leverage: "",
  margin_mode: "ISOLATED",
  hedge_mode: false,
  broadcast_trade_enabled: false,
  api_key: "",
  api_secret: "",
  api_passphrase: ""
});

export const initialFollowerDraft = (): FollowerDraft => ({
  name: "",
  exchange: "BINANCE",
  environment: "TESTNET",
  account_group: "default",
  scale_factor: "1",
  exact_copy_mode: true,
  leverage: "10",
  margin_mode: "ISOLATED",
  hedge_mode: false,
  api_key: "",
  api_secret: "",
  api_passphrase: ""
});

export const initialCopyTradeDraft = (): CopyTradeDraft => ({
  name: "",
  signal_source_id: "",
  follower_account_id: "",
  copy_mode: "EXACT",
  scale_factor: "1",
  override_leverage: "",
  command_template: "",
  notes: "",
  enabled: true
});

export const initialBuilderDraft = (): BuilderDraft => ({
  name: "TradeNodeX Builder",
  exchange: "BINANCE",
  environment: "TESTNET",
  product_type: "USD_M",
  action: "BUY",
  symbol: "",
  order_type: "MARKET",
  quantity_mode: "ABSOLUTE",
  quantity_value: "",
  leverage: "10",
  margin_mode: "ISOLATED",
  hedge_mode: false,
  broadcast_trade: false,
  create_copy_trade_signal: false,
  signal_source_id: "",
  account_id: "",
  limit_price: "",
  stop_price: "",
  stop_loss_percent: "",
  delay_seconds: "",
  use_dca: false,
  use_fixed_size: false,
  use_entire_balance: false,
  prevent_pyramiding: false,
  close_current_position: false,
  cancel_pending_orders: false,
  conditional_pyramiding: false,
  close_in_profit_only: false,
  cancel_all_orders: false,
  cancel_dca_orders: false,
  partial_close: false,
  close_by_limit_order: false,
  close_all: false,
  close_long: false,
  close_short: false,
  take_profit_steps: []
});

export function toNumber(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function toStringAmount(value: string): string | undefined {
  return value.trim() ? value.trim() : undefined;
}

export function statusTone(status: ValidationStatus | string | null | undefined): string {
  if (status === "VERIFIED" || status === "ACTIVE" || status === "FILLED" || status === "RECONCILED" || status === "RUNNING" || status === "CONNECTED") return "good";
  if (status === "POLLING") return "warning";
  if (status === "FAILED" || status === "ERROR") return "danger";
  if (status === "PAUSED" || status === "PARTIAL" || status === "WARNING") return "warning";
  return "neutral";
}

export function emptyDashboard(): DashboardResponse {
  return {
    signal_sources: [],
    copy_trades: [],
    followers: [],
    logs: [],
    recent_executions: [],
    command_presets: [],
    runtime_metrics: [],
    performance_metrics: [],
    fx_meta: null,
    equity_summary: null,
    worker_status: null
  };
}

export function buildCommandPayload(draft: BuilderDraft) {
  return {
    name: draft.name,
    exchange: draft.exchange,
    environment: draft.environment,
    product_type: draft.product_type,
    action: draft.action,
    symbol: draft.symbol,
    order_type: draft.order_type,
    quantity_mode: draft.quantity_mode,
    quantity_value: toStringAmount(draft.quantity_value) ?? null,
    leverage: toNumber(draft.leverage) ?? null,
    margin_mode: draft.margin_mode,
    hedge_mode: draft.hedge_mode,
    broadcast_trade: draft.broadcast_trade,
    create_copy_trade_signal: draft.create_copy_trade_signal,
    signal_source_id: draft.signal_source_id || null,
    account_id: draft.account_id || null,
    limit_price: toStringAmount(draft.limit_price) ?? null,
    stop_price: toStringAmount(draft.stop_price) ?? null,
    stop_loss_percent: toStringAmount(draft.stop_loss_percent) ?? null,
    delay_seconds: toNumber(draft.delay_seconds) ?? null,
    use_dca: draft.use_dca,
    use_fixed_size: draft.use_fixed_size,
    use_entire_balance: draft.use_entire_balance,
    prevent_pyramiding: draft.prevent_pyramiding,
    close_current_position: draft.close_current_position,
    cancel_pending_orders: draft.cancel_pending_orders,
    conditional_pyramiding: draft.conditional_pyramiding,
    close_in_profit_only: draft.close_in_profit_only,
    cancel_all_orders: draft.cancel_all_orders,
    cancel_dca_orders: draft.cancel_dca_orders,
    partial_close: draft.partial_close,
    close_by_limit_order: draft.close_by_limit_order,
    close_all: draft.close_all,
    close_long: draft.close_long,
    close_short: draft.close_short,
    take_profit_steps: draft.take_profit_steps
      .filter((step) => step.amount || step.takeProfitPercent)
      .map((step, index) => ({
        id: step.id || String(index + 1),
        amount: toStringAmount(step.amount) ?? "0",
        takeProfitPercent: toStringAmount(step.takeProfitPercent) ?? "0"
      }))
  };
}
