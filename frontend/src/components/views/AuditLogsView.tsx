import { RefreshCcw } from "lucide-react";

import { formatTimestamp } from "../../lib/format";
import type { TradeLog, TradeLogListResponse } from "../../types";
import { EmptyStatePanel } from "../primitives/EmptyStatePanel";
import { SectionHeader } from "../primitives/SectionHeader";
import { StatusPill } from "../primitives/StatusPill";
import { TerminalButton } from "../primitives/TerminalButton";

type LogFilters = {
  page: number;
  limit: number;
  exchange: string;
  log_type: string;
  search: string;
  sort_by: string;
  sort_order: string;
};

type Props = {
  logsPage: TradeLogListResponse;
  selectedLog: TradeLog | null;
  logFilters: LogFilters;
  locale: string;
  tr: (key: string) => string;
  onRefresh: () => void;
  onLogFiltersChange: (filters: LogFilters) => void;
  onApply: (filters?: LogFilters) => void;
  onSelectLog: (log: TradeLog) => void;
  onOpenAudit: (taskId: string) => void;
};

export function AuditLogsView(props: Props) {
  const { logFilters, logsPage, selectedLog, tr } = props;
  return (
    <section className="panel">
      <SectionHeader
        eyebrow={tr("logs")}
        title="Real-time Command Stream"
        actions={
          <TerminalButton className="secondary" type="button" onClick={props.onRefresh} icon={<RefreshCcw size={14} />}>
            {tr("refresh")}
          </TerminalButton>
        }
      />
      <div className="split-shell logs-layout">
        <div className="table-panel terminal-surface">
          <div className="filter-bar">
            <select value={logFilters.exchange} onChange={(e) => props.onLogFiltersChange({ ...logFilters, exchange: e.target.value, page: 1 })}>
              <option value="">All Exchanges</option>
              {["BINANCE", "BYBIT", "OKX", "COINBASE", "KRAKEN", "BITMEX", "GATEIO"].map((exchange) => <option key={exchange} value={exchange}>{exchange}</option>)}
            </select>
            <select value={logFilters.log_type} onChange={(e) => props.onLogFiltersChange({ ...logFilters, log_type: e.target.value, page: 1 })}>
              <option value="">All Types</option>
              {["INFO", "WARNING", "ERROR", "EXECUTION", "RECONCILE", "MANUAL", "SIGNAL"].map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
            <select value={logFilters.sort_by} onChange={(e) => props.onLogFiltersChange({ ...logFilters, sort_by: e.target.value })}>
              <option value="timestamp">Timestamp</option>
              <option value="pnl">PnL</option>
            </select>
            <select value={logFilters.sort_order} onChange={(e) => props.onLogFiltersChange({ ...logFilters, sort_order: e.target.value })}>
              <option value="desc">DESC</option>
              <option value="asc">ASC</option>
            </select>
            <input value={logFilters.search} onChange={(e) => props.onLogFiltersChange({ ...logFilters, search: e.target.value })} placeholder={tr("searchPlaceholder")} />
            <TerminalButton className="secondary small" type="button" onClick={() => props.onApply()}>{tr("apply")}</TerminalButton>
            <TerminalButton className="secondary small" type="button" onClick={() => {
              const next = { ...logFilters, page: 1 };
              props.onLogFiltersChange(next);
              props.onApply(next);
            }}>{tr("latest")}</TerminalButton>
          </div>
          <table className="terminal-table">
            <thead>
              <tr>
                <th>{tr("timestamp")}</th>
                <th>{tr("exchange")}</th>
                <th>{tr("type")}</th>
                <th>{tr("key")}</th>
                <th>{tr("pnl")}</th>
                <th>{tr("message")}</th>
              </tr>
            </thead>
            <tbody>
              {logsPage.items.length ? logsPage.items.map((log) => (
                <tr key={log.id} onClick={() => props.onSelectLog(log)}>
                  <td>{formatTimestamp(log.timestamp, props.locale)}</td>
                  <td>{log.exchange}</td>
                  <td><StatusPill value={log.log_type} /></td>
                  <td>{log.log_key}</td>
                  <td className={Number(log.pnl ?? 0) >= 0 ? "tone-good" : "tone-danger"}>{log.pnl ?? "--"}</td>
                  <td>{log.message}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={6}>
                    <div className="table-empty">No audit logs match the current filters.</div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <div className="pagination-bar">
            <div className="page-size-group">
              {[50, 100, 200].map((limit) => (
                <TerminalButton key={limit} type="button" className={logFilters.limit === limit ? "is-active" : ""} onClick={() => {
                  const next = { ...logFilters, limit, page: 1 };
                  props.onLogFiltersChange(next);
                  props.onApply(next);
                }}>
                  {limit}
                </TerminalButton>
              ))}
            </div>
            <div className="pagination-meta">{logsPage.total} records {" · "} page {logsPage.page} / {logsPage.page_count}</div>
            <div className="page-list">
              {Array.from({ length: logsPage.page_count }, (_, index) => index + 1).slice(0, 8).map((page) => (
                <TerminalButton key={page} type="button" className={logsPage.page === page ? "is-active" : ""} onClick={() => {
                  const next = { ...logFilters, page };
                  props.onLogFiltersChange(next);
                  props.onApply(next);
                }}>{page}</TerminalButton>
              ))}
            </div>
          </div>
        </div>
        <div className="detail-panel terminal-surface">
          {selectedLog ? (
            <>
              <div className="panel-inline-head"><h3>Log Detail</h3></div>
              <div className="detail-grid">
                <div><span>Exchange</span><strong>{selectedLog.exchange}</strong></div>
                <div><span>Type</span><strong>{selectedLog.log_type}</strong></div>
                <div><span>Signal</span><strong>{selectedLog.linked_signal_id ?? "--"}</strong></div>
                <div><span>Follower</span><strong>{selectedLog.linked_follower_name ?? selectedLog.linked_follower_id ?? "--"}</strong></div>
                <div><span>Task</span><strong>{selectedLog.linked_task_id ?? "--"}</strong></div>
                <div><span>Timestamp</span><strong>{formatTimestamp(selectedLog.timestamp, props.locale)}</strong></div>
              </div>
              <pre className="json-view">{JSON.stringify(selectedLog.details, null, 2)}</pre>
              {selectedLog.exchange_response ? <pre className="json-view">{JSON.stringify(selectedLog.exchange_response, null, 2)}</pre> : null}
              {selectedLog.linked_task_id ? (
                <TerminalButton className="primary chain-button" type="button" onClick={() => props.onOpenAudit(selectedLog.linked_task_id as string)}>
                  Open Signal Chain
                </TerminalButton>
              ) : null}
            </>
          ) : (
            <EmptyStatePanel title="Log Inspector" description="Select a log row to inspect linked ids, raw payload, and exchange response detail." />
          )}
        </div>
      </div>
    </section>
  );
}
