import { environmentsForExchange, exchanges, normalizeEnvironment, type BuilderDraft } from "../../../lib/app-model";
import type { Follower, SignalSource } from "../../../types";
import { TerminalButton } from "../../primitives/TerminalButton";

type SharedProps = {
  draft: BuilderDraft;
  onDraftChange: (draft: BuilderDraft) => void;
  signals: SignalSource[];
  followers: Follower[];
  instrumentOptions: Array<{ label: string; value: string }>;
  tr: (key: string) => string;
};

export function StudioIdentitySection({ draft, onDraftChange, signals, followers, instrumentOptions, tr }: SharedProps) {
  const filteredFollowers = followers.filter((item) => item.exchange === draft.exchange && item.environment === draft.environment);
  const environmentOptions = environmentsForExchange(draft.exchange);

  return (
    <div className="form-grid">
      <label><span>Name</span><input value={draft.name} onChange={(e) => onDraftChange({ ...draft, name: e.target.value })} /></label>
      <label><span>{tr("exchange")}</span><select value={draft.exchange} onChange={(e) => {
        const exchange = e.target.value;
        onDraftChange({ ...draft, exchange, environment: normalizeEnvironment(exchange, draft.environment), account_id: "", symbol: "" });
      }}>{exchanges.map((exchange) => <option key={exchange} value={exchange}>{exchange}</option>)}</select></label>
      <label><span>{tr("environment")}</span><select value={draft.environment} onChange={(e) => onDraftChange({ ...draft, environment: e.target.value, account_id: "" })}>{environmentOptions.map((environment) => <option key={environment} value={environment}>{environment}</option>)}</select></label>
      <label><span>{tr("signal")}</span><select value={draft.signal_source_id} onChange={(e) => onDraftChange({ ...draft, signal_source_id: e.target.value })}><option value="">Select</option>{signals.map((signal) => <option key={signal.id} value={signal.id}>{signal.name}</option>)}</select></label>
      <label><span>{tr("follower")}</span><select value={draft.account_id} onChange={(e) => onDraftChange({ ...draft, account_id: e.target.value })}><option value="">Select</option>{filteredFollowers.map((follower) => <option key={follower.id} value={follower.id}>{follower.name}</option>)}</select></label>
      <label>
        <span>{tr("symbol")}</span>
        <input list="instrument-list" value={draft.symbol} onChange={(e) => onDraftChange({ ...draft, symbol: e.target.value.toUpperCase() })} required />
        <datalist id="instrument-list">{instrumentOptions.map((instrument) => <option key={instrument.value} value={instrument.value}>{instrument.label}</option>)}</datalist>
      </label>
    </div>
  );
}

export function StudioProductTabs({ draft, onDraftChange }: Pick<SharedProps, "draft" | "onDraftChange">) {
  return (
    <div className="product-tabs terminal-surface">
      {["USD_M", "COIN_M"].map((tab) => (
        <TerminalButton key={tab} type="button" className={draft.product_type === tab ? "is-active" : ""} onClick={() => onDraftChange({ ...draft, product_type: tab })}>
          {tab}
        </TerminalButton>
      ))}
    </div>
  );
}

export function StudioActionTabs({ draft, onDraftChange }: Pick<SharedProps, "draft" | "onDraftChange">) {
  return (
    <div className="action-tabs terminal-surface">
      {(["BUY", "SELL", "CANCEL_ORDERS", "CLOSE_POSITION"] as const).map((action) => (
        <TerminalButton key={action} type="button" className={draft.action === action ? `is-active action-${action.toLowerCase()}` : ""} onClick={() => onDraftChange({ ...draft, action })}>
          {action}
        </TerminalButton>
      ))}
    </div>
  );
}

export function StudioActionSection({ draft, onDraftChange, tr }: Pick<SharedProps, "draft" | "onDraftChange" | "tr">) {
  if (draft.action === "BUY" || draft.action === "SELL") {
    return (
      <section className="studio-section terminal-subsection">
        <h4>Order Entry</h4>
        <div className="form-grid">
          <label><span>Order Type</span><select value={draft.order_type} onChange={(e) => onDraftChange({ ...draft, order_type: e.target.value })}><option value="MARKET">MARKET</option><option value="LIMIT">LIMIT</option><option value="STOP_MARKET">STOP_MARKET</option></select></label>
          <label><span>Quantity</span><input value={draft.quantity_value} onChange={(e) => onDraftChange({ ...draft, quantity_value: e.target.value })} /></label>
          <label><span>{tr("leverage")}</span><input value={draft.leverage} onChange={(e) => onDraftChange({ ...draft, leverage: e.target.value })} /></label>
          <label><span>Margin Mode</span><select value={draft.margin_mode} onChange={(e) => onDraftChange({ ...draft, margin_mode: e.target.value })}><option value="ISOLATED">ISOLATED</option><option value="CROSS">CROSS</option></select></label>
          <label><span>Limit Price</span><input value={draft.limit_price} onChange={(e) => onDraftChange({ ...draft, limit_price: e.target.value })} /></label>
          <label><span>Stop Price</span><input value={draft.stop_price} onChange={(e) => onDraftChange({ ...draft, stop_price: e.target.value })} /></label>
          <label><span>Stop Loss %</span><input value={draft.stop_loss_percent} onChange={(e) => onDraftChange({ ...draft, stop_loss_percent: e.target.value })} /></label>
          <label><span>Delay Seconds</span><input value={draft.delay_seconds} onChange={(e) => onDraftChange({ ...draft, delay_seconds: e.target.value })} /></label>
        </div>
      </section>
    );
  }

  if (draft.action === "CANCEL_ORDERS") {
    return (
      <section className="studio-section terminal-subsection">
        <h4>Cancel Scope</h4>
        <div className="toggle-grid">
          {(["cancel_all_orders", "cancel_dca_orders", "broadcast_trade"] as const).map((key) => (
            <label key={key} className="toggle-row"><input type="checkbox" checked={Boolean(draft[key])} onChange={(e) => onDraftChange({ ...draft, [key]: e.target.checked })} /><span>{key}</span></label>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="studio-section terminal-subsection">
      <h4>Close Position Scope</h4>
      <div className="toggle-grid">
        {(["partial_close", "close_by_limit_order", "close_all", "close_long", "close_short", "close_in_profit_only"] as const).map((key) => (
          <label key={key} className="toggle-row"><input type="checkbox" checked={Boolean(draft[key])} onChange={(e) => onDraftChange({ ...draft, [key]: e.target.checked })} /><span>{key}</span></label>
        ))}
      </div>
    </section>
  );
}

export function StudioRiskSection({ draft, onDraftChange }: Pick<SharedProps, "draft" | "onDraftChange">) {
  return (
    <section className="studio-section terminal-subsection">
      <h4>Risk Controls</h4>
      <div className="toggle-grid">
        {(["hedge_mode", "broadcast_trade", "create_copy_trade_signal", "use_dca", "use_fixed_size", "use_entire_balance", "prevent_pyramiding", "close_current_position", "cancel_pending_orders", "conditional_pyramiding"] as const).map((key) => (
          <label key={key} className="toggle-row"><input type="checkbox" checked={Boolean(draft[key])} onChange={(e) => onDraftChange({ ...draft, [key]: e.target.checked })} /><span>{key}</span></label>
        ))}
      </div>
    </section>
  );
}
