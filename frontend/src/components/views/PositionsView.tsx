import type { ReactNode } from "react";
import { RefreshCcw, AlertCircle, CheckCircle2, ChevronRight, Wallet } from "lucide-react";

import { formatDisplay, formatTimestamp } from "../../lib/format";
import type { EquitySummary, PositionSnapshot } from "../../types";
import { SectionHeader } from "../primitives/SectionHeader";
import { StatusPill } from "../primitives/StatusPill";
import { TerminalButton } from "../primitives/TerminalButton";

type Props = {
  positions: PositionSnapshot[];
  equitySummary: EquitySummary | null;
  displayCurrency: string;
  locale: string;
  tr: (key: string) => string;
  onRefresh: () => void;
};

export function PositionsView({ positions, equitySummary, displayCurrency, locale, tr, onRefresh }: Props) {
  return (
    <section className="panel">
      <SectionHeader
        eyebrow={tr("positions")}
        title="Live Asset Allocation"
        actions={
          <TerminalButton className="secondary" type="button" onClick={onRefresh} icon={<RefreshCcw size={14} />}>
            {tr("sync")}
          </TerminalButton>
        }
      />
      <div className="metric-grid equity-grid">
        {equitySummary ? (
          <>
            {metricCard("Total Notional", formatDisplay(equitySummary.total_notional, locale, displayCurrency), "neutral", displayCurrency, <Wallet size={16} />)}
            {metricCard("Long Exposure", formatDisplay(equitySummary.long_exposure, locale, displayCurrency), "good", displayCurrency, <CheckCircle2 size={16} />)}
            {metricCard("Short Exposure", formatDisplay(equitySummary.short_exposure, locale, displayCurrency), "warning", displayCurrency, <ChevronRight size={16} />)}
            {metricCard("Stale Snapshots", String(equitySummary.stale_snapshots), equitySummary.stale_snapshots ? "danger" : "good", "position freshness", <AlertCircle size={16} />)}
          </>
        ) : null}
      </div>
      <div className="table-panel terminal-surface">
        <table className="terminal-table">
          <thead>
            <tr>
              <th>Instrument</th>
              <th>{tr("exchange")}</th>
              <th>{tr("exposure")}</th>
              <th>Entry / Mark</th>
              <th>{tr("pnl")}</th>
              <th>{tr("leverage")}</th>
              <th>{tr("freshness")}</th>
              <th>{tr("captured")}</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <tr key={position.id}>
                <td>
                  <div className="table-title">{position.symbol}</div>
                  <div className="table-sub">{position.follower_name ?? position.source}</div>
                </td>
                <td>{position.exchange}</td>
                <td>{formatDisplay(position.display_value ?? position.notional_exposure, locale, displayCurrency)}</td>
                <td>
                  <div className="stack-cell">
                    <span>{formatDisplay(position.entry_price, locale)}</span>
                    <small>{formatDisplay(position.mark_price, locale)}</small>
                  </div>
                </td>
                <td className={Number(position.unrealized_pnl ?? 0) >= 0 ? "tone-good" : "tone-danger"}>{formatDisplay(position.unrealized_pnl, locale, displayCurrency)}</td>
                <td>{position.leverage ?? "--"} {position.margin_mode ? `· ${position.margin_mode}` : ""}</td>
                <td><StatusPill value={position.freshness === "stale" ? "FAILED" : position.freshness === "aging" ? "WARNING" : "VERIFIED"} /></td>
                <td>{formatTimestamp(position.captured_at, locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function metricCard(label: string, value: string, tone: string, note: string, icon: ReactNode) {
  return (
    <article className="metric-card is-emphasis terminal-surface">
      <div className="metric-topline">
        <span className="metric-label">{label}</span>
        <span className={`metric-icon tone-${tone}`}>{icon}</span>
      </div>
      <strong className={`metric-value tone-${tone}`}>{value}</strong>
      <span className="metric-note">{note}</span>
    </article>
  );
}
