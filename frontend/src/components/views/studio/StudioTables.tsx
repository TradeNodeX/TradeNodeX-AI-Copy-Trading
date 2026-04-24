import { formatTimestamp } from "../../../lib/format";
import type { CommandPreset, ExecutionTask, SignalSource } from "../../../types";
import { StatusPill } from "../../primitives/StatusPill";

type PresetsProps = {
  presets: CommandPreset[];
  signals: SignalSource[];
  selectedPresetId: string | null;
  locale: string;
  exchangeLabel: string;
  signalLabel: string;
  onPresetSelect: (presetId: string) => void;
};

export function StudioPresetsTable(props: PresetsProps) {
  return (
    <div className="table-panel terminal-surface">
      <div className="panel-inline-head"><h3>Saved Presets</h3></div>
      <table className="terminal-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>{props.exchangeLabel}</th>
            <th>{props.signalLabel}</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {props.presets.length ? props.presets.map((preset) => (
            <tr key={preset.id} className={props.selectedPresetId === preset.id ? "is-selected" : ""} onClick={() => props.onPresetSelect(preset.id)}>
              <td>{preset.name}</td>
              <td>{preset.exchange}</td>
              <td>{props.signals.find((item) => item.id === preset.signal_source_id)?.name ?? "--"}</td>
              <td>{formatTimestamp(preset.created_at, props.locale)}</td>
            </tr>
          )) : (
            <tr>
              <td colSpan={4}>
                <div className="table-empty">No saved presets yet.</div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

type QueueProps = {
  executions: ExecutionTask[];
  signalLabel: string;
  followerLabel: string;
  symbolLabel: string;
  statusLabel: string;
  latencyLabel: string;
  title: string;
  onOpenAudit: (taskId: string) => void;
};

export function StudioLiveQueueTable(props: QueueProps) {
  return (
    <div className="table-panel terminal-surface">
      <div className="panel-inline-head"><h3>{props.title}</h3></div>
      <table className="terminal-table">
        <thead>
          <tr>
            <th>{props.signalLabel}</th>
            <th>{props.followerLabel}</th>
            <th>{props.symbolLabel}</th>
            <th>{props.statusLabel}</th>
            <th>{props.latencyLabel}</th>
          </tr>
        </thead>
        <tbody>
          {props.executions.length ? props.executions.map((task) => (
            <tr key={task.id} onClick={() => props.onOpenAudit(task.id)}>
              <td>{task.signal_name ?? task.signal_id.slice(0, 8)}</td>
              <td>{task.follower_name ?? task.follower_account_id.slice(0, 8)}</td>
              <td>{task.symbol}</td>
              <td>
                <div className="stack-cell">
                  <StatusPill value={task.exchange_stage ?? task.status} />
                  <small>{task.latest_attempt_status ?? task.status}</small>
                </div>
              </td>
              <td>{task.queue_latency_ms ? `${task.queue_latency_ms}ms` : "--"}</td>
            </tr>
          )) : (
            <tr>
              <td colSpan={5}>
                <div className="table-empty">No live execution tasks in queue.</div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
