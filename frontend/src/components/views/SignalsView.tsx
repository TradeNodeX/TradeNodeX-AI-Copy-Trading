import { Plus, RefreshCcw } from "lucide-react";

import { statusTone } from "../../lib/app-model";
import type { SignalSource } from "../../types";
import { SectionHeader } from "../primitives/SectionHeader";
import { StatusPill } from "../primitives/StatusPill";
import { TerminalButton } from "../primitives/TerminalButton";

type Props = {
  signals: SignalSource[];
  tr: (key: string) => string;
  onRefresh: () => void;
  onCreate: () => void;
  onEdit: (signal: SignalSource) => void;
  onValidate: (signalId: string) => void;
  onBuild: (signal: SignalSource) => void;
};

export function SignalsView({ signals, tr, onRefresh, onCreate, onEdit, onValidate, onBuild }: Props) {
  return (
    <section className="panel">
      <SectionHeader
        eyebrow={tr("signals")}
        title="Operational Signals"
        actions={
          <>
            <TerminalButton className="secondary" type="button" onClick={onRefresh} icon={<RefreshCcw size={14} />}>
              {tr("refresh")}
            </TerminalButton>
            <TerminalButton className="primary" type="button" onClick={onCreate} icon={<Plus size={14} />}>
              {tr("addSignal")}
            </TerminalButton>
          </>
        }
      />
      <div className="signal-grid">
        {signals.map((signal) => (
          <article key={signal.id} className={`signal-card status-${statusTone(signal.status)} terminal-surface`}>
            <div className="signal-head">
              <div className="signal-title-stack">
                <h3>{signal.name}</h3>
                <div className="pill-row">
                  <span className="outline-pill">{signal.exchange}</span>
                  <span className="outline-pill">{signal.environment}</span>
                  <span className="outline-pill">{signal.default_copy_mode}</span>
                </div>
              </div>
              <StatusPill value={signal.status} />
            </div>
            <div className="signal-stats compact">
              <div className="signal-stat">
                <span>Followers</span>
                <strong>{signal.follower_count}</strong>
              </div>
              <div className="signal-stat">
                <span>Pairs</span>
                <strong>{signal.pairs_scope}</strong>
              </div>
              <div className="signal-stat">
                <span>Routing</span>
                <strong>{signal.broadcast_trade_enabled ? "BROADCAST" : "DIRECT-DMA"}</strong>
              </div>
              <div className="signal-stat">
                <span>Leverage</span>
                <strong>{signal.default_leverage ?? "AUTO"}</strong>
              </div>
              <div className="signal-stat">
                <span>Listener</span>
                <strong>{signal.listener_status}</strong>
              </div>
              <div className="signal-stat">
                <span>Stream</span>
                <strong>{signal.stream_status}</strong>
              </div>
            </div>
            <div className="signal-trace">
              <div className="follower-preview">
                {(signal.follower_names.length ? signal.follower_names.slice(0, 2) : ["No followers attached."]).map((name) => (
                  <span key={name} className="outline-pill small">{name}</span>
                ))}
                {signal.follower_names.length > 2 ? <span className="outline-pill small">+{signal.follower_names.length - 2}</span> : null}
              </div>
              {signal.validation_reasons.length ? (
                <div className="reason-strip">{signal.validation_reasons[0]}</div>
              ) : (
                <div className="signal-footer-note">
                  {signal.last_stream_event_at ? `Last event ${new Date(signal.last_stream_event_at).toLocaleString()}` : "No validation warnings."}
                </div>
              )}
            </div>
            <div className="card-actions signal-card-actions">
              <TerminalButton type="button" onClick={() => onEdit(signal)}>{tr("edit")}</TerminalButton>
              <TerminalButton type="button" onClick={() => onValidate(signal.id)}>{tr("validate")}</TerminalButton>
              <TerminalButton className="strong" type="button" onClick={() => onBuild(signal)}>{tr("build")}</TerminalButton>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
