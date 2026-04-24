import { Plus, RefreshCcw } from "lucide-react";

import type { CopyTrade, Follower, SignalSource } from "../../types";
import type { CopyTradeDraft } from "../../lib/app-model";
import { EmptyStatePanel } from "../primitives/EmptyStatePanel";
import { SectionHeader } from "../primitives/SectionHeader";
import { StatusPill } from "../primitives/StatusPill";
import { TerminalButton } from "../primitives/TerminalButton";

type Props = {
  copyTrades: CopyTrade[];
  followers: Follower[];
  signals: SignalSource[];
  selectedCopyTrade: CopyTrade | null;
  draft: CopyTradeDraft;
  tr: (key: string) => string;
  onRefresh: () => void;
  onCreate: () => void;
  onSelect: (id: string) => void;
  onDraftChange: (draft: CopyTradeDraft) => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onDelete: () => void;
};

export function CopyTradesView(props: Props) {
  const { copyTrades, followers, signals, selectedCopyTrade, draft, tr } = props;

  return (
    <section className="panel">
      <SectionHeader
        eyebrow={tr("copyTrades")}
        title="Automated Signal Mappings"
        actions={
          <>
            <TerminalButton className="secondary" type="button" onClick={props.onRefresh} icon={<RefreshCcw size={14} />}>
              {tr("refresh")}
            </TerminalButton>
            <TerminalButton className="primary" type="button" onClick={props.onCreate} icon={<Plus size={14} />}>
              {tr("addCopyTrade")}
            </TerminalButton>
          </>
        }
      />
      <div className="split-shell">
        <div className="table-panel terminal-surface">
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>{tr("signal")}</th>
                <th>{tr("status")}</th>
                <th>{tr("readiness")}</th>
              </tr>
            </thead>
            <tbody>
              {copyTrades.length ? copyTrades.map((trade) => (
                <tr key={trade.id} className={selectedCopyTrade?.id === trade.id ? "is-selected" : ""} onClick={() => props.onSelect(trade.id)}>
                  <td>
                    <div className="table-title">{trade.name}</div>
                    <div className="table-sub">{trade.follower_name}</div>
                  </td>
                  <td>{trade.signal_name}</td>
                  <td><StatusPill value={trade.status} /></td>
                  <td><StatusPill value={trade.validation_status} /></td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={4}>
                    <div className="table-empty">No copy-trade mappings provisioned yet.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="editor-panel terminal-surface">
          <div className="editor-header">
            <div className="editor-title-block">
              <p className="eyebrow">{tr("copyTrades")}</p>
              <h3>{selectedCopyTrade ? selectedCopyTrade.name : tr("createRoute")}</h3>
              <p className="editor-subtitle">
                {selectedCopyTrade
                  ? `${selectedCopyTrade.signal_name} -> ${selectedCopyTrade.follower_name}`
                  : "Configure signal-to-follower execution with exact or scaled routing."}
              </p>
            </div>
          </div>
          {selectedCopyTrade || draft.name ? (
            <form className="editor-form" onSubmit={props.onSubmit}>
              <section className="editor-section">
                <h4>Base Binding</h4>
                <div className="form-grid">
                  <label>
                    <span>Name</span>
                    <input value={draft.name} onChange={(e) => props.onDraftChange({ ...draft, name: e.target.value })} required />
                  </label>
                  <label>
                    <span>{tr("signal")}</span>
                    <select value={draft.signal_source_id} onChange={(e) => props.onDraftChange({ ...draft, signal_source_id: e.target.value })}>
                      <option value="">Select</option>
                      {signals.map((signal) => <option key={signal.id} value={signal.id}>{signal.name}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>{tr("follower")}</span>
                    <select value={draft.follower_account_id} onChange={(e) => props.onDraftChange({ ...draft, follower_account_id: e.target.value })}>
                      <option value="">Select</option>
                      {followers.map((follower) => <option key={follower.id} value={follower.id}>{follower.name}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>Override Leverage</span>
                    <input value={draft.override_leverage} onChange={(e) => props.onDraftChange({ ...draft, override_leverage: e.target.value })} />
                  </label>
                </div>
              </section>
              <section className="editor-section">
                <h4>Copy Mode</h4>
                <div className={draft.copy_mode === "EXACT" ? "exact-copy-callout is-active" : "exact-copy-callout"}>
                  <strong>EXACT 1:1 IS THE REAL FOLLOW-SIZING SWITCH</strong>
                  <span>When EXACT is active, follower order quantity mirrors the master quantity. Scale factor is ignored and consistency checks enforce environment, leverage, margin mode, and hedge mode.</span>
                </div>
                <div className="mode-selector">
                  <TerminalButton type="button" className={draft.copy_mode === "EXACT" ? "is-selected" : ""} onClick={() => props.onDraftChange({ ...draft, copy_mode: "EXACT" })}>
                    1:1 EXACT
                  </TerminalButton>
                  <TerminalButton type="button" className={draft.copy_mode === "SCALE" ? "is-selected" : ""} onClick={() => props.onDraftChange({ ...draft, copy_mode: "SCALE" })}>
                    {tr("scale")}
                  </TerminalButton>
                </div>
                {draft.copy_mode === "SCALE" ? (
                  <label>
                    <span>Scale Factor</span>
                    <input value={draft.scale_factor} onChange={(e) => props.onDraftChange({ ...draft, scale_factor: e.target.value })} />
                  </label>
                ) : <p className="field-hint">Scale Factor is disabled in EXACT mode. The backend uses master quantity exactly after symbol precision normalization.</p>}
              </section>
              <section className="editor-section">
                <h4>Execution Template</h4>
                <textarea value={draft.command_template} onChange={(e) => props.onDraftChange({ ...draft, command_template: e.target.value })} rows={5} />
              </section>
              <section className="editor-section">
                <h4>Risk & Operator Notes</h4>
                <textarea value={draft.notes} onChange={(e) => props.onDraftChange({ ...draft, notes: e.target.value })} rows={3} />
              </section>
              {selectedCopyTrade?.validation_reasons.length ? (
                <div className="reason-list">
                  <h4>{tr("validationReasons")}</h4>
                  <ul>{selectedCopyTrade.validation_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                </div>
              ) : null}
              <label className="toggle-row">
                <input type="checkbox" checked={draft.enabled} onChange={(e) => props.onDraftChange({ ...draft, enabled: e.target.checked })} />
                <span>Enabled</span>
              </label>
              <div className="editor-actions">
                {draft.id ? <TerminalButton type="button" className="danger" onClick={props.onDelete}>{tr("delete")}</TerminalButton> : null}
                <TerminalButton type="submit" className="primary">{tr("save")}</TerminalButton>
              </div>
            </form>
          ) : <EmptyStatePanel title="Copy Route Editor" description="Select a mapping from the table or create a new route to configure signal-to-follower execution." />}
        </div>
      </div>
    </section>
  );
}
