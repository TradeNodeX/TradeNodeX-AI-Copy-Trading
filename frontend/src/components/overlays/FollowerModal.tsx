import { X } from "lucide-react";
import { environmentsForExchange, normalizeEnvironment, type FollowerDraft } from "../../lib/app-model";

type Props = {
  open: boolean;
  draft: FollowerDraft;
  tr: (key: string) => string;
  onClose: () => void;
  onDraftChange: (draft: FollowerDraft) => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onValidate?: () => void;
  onDelete?: () => void;
};

export function FollowerModal({ open, draft, tr, onClose, onDraftChange, onSubmit, onValidate, onDelete }: Props) {
  if (!open) return null;
  const environmentOptions = environmentsForExchange(draft.exchange);
  const okxPassphraseRequired = draft.exchange === "OKX" && !draft.id;
  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div className="modal-card terminal-surface" onClick={(event) => event.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <p className="eyebrow">{tr("apiRegistry")}</p>
            <h3>{draft.id ? tr("edit") : tr("createApi")}</h3>
          </div>
          <button className="icon-button" type="button" onClick={onClose}><X size={16} /></button>
        </div>
        <form className="editor-form" onSubmit={onSubmit}>
          <div className="security-panel compact">
            <div className="security-title">{tr("securityTitle")}</div>
            <ul>
              <li>{tr("tradeOnly")}</li>
              <li>{tr("noWithdrawals")}</li>
              <li>{tr("whitelist")}</li>
              <li>{tr("okxPassphrase")}</li>
            </ul>
          </div>
          <div className="form-grid">
            <label><span>Name</span><input value={draft.name} onChange={(e) => onDraftChange({ ...draft, name: e.target.value })} required /></label>
            <label><span>{tr("exchange")}</span><select value={draft.exchange} onChange={(e) => {
              const exchange = e.target.value;
              onDraftChange({ ...draft, exchange, environment: normalizeEnvironment(exchange, draft.environment) });
            }}>{["BINANCE", "BYBIT", "OKX", "COINBASE", "KRAKEN", "BITMEX", "GATEIO"].map((exchange) => <option key={exchange} value={exchange}>{exchange}</option>)}</select></label>
            <label><span>{tr("environment")}</span><select value={draft.environment} onChange={(e) => onDraftChange({ ...draft, environment: e.target.value })}>{environmentOptions.map((environment) => <option key={environment} value={environment}>{environment}</option>)}</select></label>
            <label><span>Account Group</span><input value={draft.account_group} onChange={(e) => onDraftChange({ ...draft, account_group: e.target.value })} /></label>
            <label><span>Scale Factor</span><input value={draft.scale_factor} onChange={(e) => onDraftChange({ ...draft, scale_factor: e.target.value })} /></label>
            <label><span>{tr("leverage")}</span><input value={draft.leverage} onChange={(e) => onDraftChange({ ...draft, leverage: e.target.value })} /></label>
          </div>
          <div className="form-grid">
            <label><span>API Key</span><input value={draft.api_key} onChange={(e) => onDraftChange({ ...draft, api_key: e.target.value })} /></label>
            <label><span>API Secret</span><input value={draft.api_secret} onChange={(e) => onDraftChange({ ...draft, api_secret: e.target.value })} /></label>
            <label><span>API Passphrase{draft.exchange === "OKX" ? " *" : ""}</span><input value={draft.api_passphrase} onChange={(e) => onDraftChange({ ...draft, api_passphrase: e.target.value })} required={okxPassphraseRequired} placeholder={draft.exchange === "OKX" ? "Required for OKX" : ""} /></label>
          </div>
          <div className="toggle-grid">
            <label className="toggle-row"><input type="checkbox" checked={draft.exact_copy_mode} onChange={(e) => onDraftChange({ ...draft, exact_copy_mode: e.target.checked })} /><span>{tr("exact")}</span></label>
            <label className="toggle-row"><input type="checkbox" checked={draft.hedge_mode} onChange={(e) => onDraftChange({ ...draft, hedge_mode: e.target.checked })} /><span>Hedge Mode</span></label>
          </div>
          <div className="editor-actions">
            {draft.id ? <button type="button" className="secondary" onClick={onValidate}>{tr("validate")}</button> : null}
            {draft.id ? <button type="button" className="danger" onClick={onDelete}>{tr("delete")}</button> : null}
            <button type="submit" className="primary">{tr("save")}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
