import { Plus, RefreshCcw } from "lucide-react";

import { ReadinessBadge } from "../ReadinessBadge";
import { EmptyStatePanel } from "../primitives/EmptyStatePanel";
import { SectionHeader } from "../primitives/SectionHeader";
import { StatusPill } from "../primitives/StatusPill";
import { TerminalButton } from "../primitives/TerminalButton";
import type { Follower, SignalSource } from "../../types";

type Props = {
  signals: SignalSource[];
  followers: Follower[];
  tr: (key: string) => string;
  onRefresh: () => void;
  onCreateSignal: () => void;
  onCreateFollower: () => void;
  onEditSignal: (signal: SignalSource) => void;
  onValidateSignal: (id: string) => void;
  onEditFollower: (follower: Follower) => void;
  onValidateFollower: (id: string) => void;
  onToggleFollowerStatus: (follower: Follower) => void;
};

export function ApiRegistryView(props: Props) {
  return (
    <section className="panel">
      <SectionHeader
        eyebrow={props.tr("apiRegistry")}
        title="Credential Management"
        actions={
          <>
            <TerminalButton className="secondary" type="button" onClick={props.onCreateFollower} icon={<Plus size={14} />}>
              {props.tr("addApi")}
            </TerminalButton>
            <TerminalButton className="primary" type="button" onClick={props.onCreateSignal} icon={<Plus size={14} />}>
              {props.tr("addSignal")}
            </TerminalButton>
          </>
        }
      />
      <div className="security-panel terminal-surface">
        <div className="security-title">{props.tr("securityTitle")}</div>
        <ul>
          <li>{props.tr("tradeOnly")}</li>
          <li>{props.tr("noWithdrawals")}</li>
          <li>{props.tr("whitelist")}</li>
          <li>{props.tr("okxPassphrase")}</li>
          <li>{props.tr("encrypted")}</li>
        </ul>
      </div>
      <div className="split-shell">
        <div className="table-panel terminal-surface">
          <div className="panel-inline-head">
            <h3>{props.tr("signalSources")}</h3>
            <TerminalButton className="secondary small" type="button" onClick={props.onRefresh} icon={<RefreshCcw size={12} />}>
              {props.tr("refresh")}
            </TerminalButton>
          </div>
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>{props.tr("exchange")}</th>
                <th>{props.tr("readiness")}</th>
                <th>Listener</th>
                <th>{props.tr("status")}</th>
              </tr>
            </thead>
            <tbody>
              {props.signals.length ? props.signals.map((signal) => (
                <tr key={signal.id}>
                  <td>
                    <div className="table-title">{signal.name}</div>
                    <div className="table-sub">{signal.source_account}</div>
                  </td>
                  <td>{signal.exchange}</td>
                  <td>
                    <div className="readiness-stack">
                      <ReadinessBadge label="Credential" status={signal.credential_status} />
                      <ReadinessBadge label="Permission" status={signal.permission_status} />
                      <ReadinessBadge label="Connectivity" status={signal.connectivity_status} />
                      <ReadinessBadge label="Trading Ready" status={signal.trading_ready_status} />
                    </div>
                  </td>
                  <td>
                    <div className="readiness-stack">
                      <ReadinessBadge label="Listener" status={signal.listener_status} />
                      <ReadinessBadge label="Stream" status={signal.stream_status} />
                    </div>
                    <div className="table-sub">{signal.last_stream_event_at ? new Date(signal.last_stream_event_at).toLocaleString() : "No stream events yet"}</div>
                  </td>
                  <td>
                    <div className="action-cell">
                      <TerminalButton type="button" onClick={() => props.onEditSignal(signal)}>{props.tr("edit")}</TerminalButton>
                      <TerminalButton type="button" onClick={() => props.onValidateSignal(signal.id)}>{props.tr("validate")}</TerminalButton>
                    </div>
                    <div className="row-status-meta">
                      <StatusPill value={signal.status} />
                    </div>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={5}>
                    <div className="table-empty">No signal source credentials provisioned yet.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="table-panel terminal-surface">
          <div className="panel-inline-head">
            <h3>{props.tr("apiAccounts")}</h3>
            <TerminalButton className="secondary small" type="button" onClick={props.onRefresh} icon={<RefreshCcw size={12} />}>
              {props.tr("refresh")}
            </TerminalButton>
          </div>
          <table className="terminal-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>{props.tr("exchange")}</th>
                <th>{props.tr("readiness")}</th>
                <th>{props.tr("status")}</th>
              </tr>
            </thead>
            <tbody>
              {props.followers.length ? props.followers.map((follower) => (
                <tr key={follower.id}>
                  <td>
                    <div className="table-title">{follower.name}</div>
                    <div className="table-sub">{follower.environment}</div>
                  </td>
                  <td>{follower.exchange}</td>
                  <td>
                    <div className="readiness-stack">
                      <ReadinessBadge label="Credential" status={follower.credential_status} />
                      <ReadinessBadge label="Permission" status={follower.permission_status} />
                      <ReadinessBadge label="Connectivity" status={follower.connectivity_status} />
                      <ReadinessBadge label="Trading Ready" status={follower.trading_ready_status} />
                    </div>
                  </td>
                  <td>
                    <div className="action-cell">
                      <TerminalButton type="button" onClick={() => props.onEditFollower(follower)}>{props.tr("edit")}</TerminalButton>
                      <TerminalButton type="button" onClick={() => props.onValidateFollower(follower.id)}>{props.tr("validate")}</TerminalButton>
                      <TerminalButton type="button" onClick={() => props.onToggleFollowerStatus(follower)}>{follower.status === "ACTIVE" ? "Pause" : "Resume"}</TerminalButton>
                    </div>
                    <div className="row-status-meta">
                      <StatusPill value={follower.status} />
                    </div>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={4}>
                    <div className="table-empty">No API accounts provisioned yet.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {!props.signals.length && !props.followers.length ? (
        <EmptyStatePanel title="Provisioning" description="Create a signal source or API account to begin validation, routing, and execution." />
      ) : null}
    </section>
  );
}
