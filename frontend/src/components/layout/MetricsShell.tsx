import { Activity, ArrowLeftRight, CheckCircle2, Cpu, Layers, ShieldCheck, Wallet } from "lucide-react";

import type { DashboardMetric, EquitySummary, FxMeta } from "../../types";

type Props = {
  runtimeMetrics: DashboardMetric[];
  performanceMetrics: DashboardMetric[];
  equitySummary: EquitySummary | null;
  fxMeta: FxMeta | null;
  tr: (key: string) => string;
};

export function MetricsShell({ runtimeMetrics, performanceMetrics, equitySummary, fxMeta, tr }: Props) {
  const runtimeIcons = [<Activity size={16} />, <Layers size={16} />, <ShieldCheck size={16} />, <Cpu size={16} />];
  const perfIcons = [<Wallet size={16} />, <ArrowLeftRight size={16} />, <Layers size={16} />, <CheckCircle2 size={16} />];
  void equitySummary;
  void fxMeta;
  void tr;

  return (
    <section className="metrics-shell">
      <div className="metric-grid">
        {runtimeMetrics.map((metric, index) => (
          <article key={metric.label} className="metric-card">
            <div className="metric-topline">
              <span className="metric-label">{metric.label}</span>
              <span className={`metric-icon tone-${metric.tone}`}>{runtimeIcons[index] ?? runtimeIcons[0]}</span>
            </div>
            <strong className={`metric-value tone-${metric.tone}`}>{String(metric.value)}</strong>
            <span className="metric-note">{metric.note ?? "--"}</span>
          </article>
        ))}
        {performanceMetrics.map((metric, index) => (
          <article key={metric.label} className="metric-card is-emphasis">
            <div className="metric-topline">
              <span className="metric-label">{metric.label}</span>
              <span className={`metric-icon tone-${metric.tone}`}>{perfIcons[index] ?? perfIcons[0]}</span>
            </div>
            <strong className={`metric-value tone-${metric.tone}`}>{String(metric.value)}</strong>
            <span className="metric-note">{metric.note ?? "--"}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
