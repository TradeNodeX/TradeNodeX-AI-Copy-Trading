import { X } from "lucide-react";
import type { ExecutionAudit } from "../../types";
import { statusTone } from "../../lib/app-model";
import { formatTimestamp } from "../../lib/format";

type Props = {
  audit: ExecutionAudit | null;
  locale: string;
  onClose: () => void;
};

export function AuditDrawer({ audit, locale, onClose }: Props) {
  if (!audit) return null;
  return (
    <div className="drawer-overlay" role="presentation" onClick={onClose}>
      <aside className="audit-drawer terminal-surface" onClick={(event) => event.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <p className="eyebrow">Execution Audit Trail</p>
            <h3>{audit.task.signal_name ?? audit.task.id}</h3>
          </div>
          <button className="icon-button" type="button" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        <div className="detail-grid">
          <div><span>Follower</span><strong>{audit.task.follower_name ?? audit.task.follower_account_id}</strong></div>
          <div><span>Exchange</span><strong>{audit.task.exchange}</strong></div>
          <div><span>Stage</span><strong>{audit.task.exchange_stage ?? audit.task.status}</strong></div>
          <div><span>Latency</span><strong>{audit.task.queue_latency_ms ? `${audit.task.queue_latency_ms}ms` : "—"}</strong></div>
        </div>
        <div className="timeline">
          {audit.timeline.map((item) => (
            <article key={item.id} className={`timeline-item tone-${statusTone(item.level)}`}>
              <div className="timeline-meta">
                <strong>{item.title}</strong>
                <span>{formatTimestamp(item.timestamp, locale)}</span>
              </div>
              <p>{item.message}</p>
            </article>
          ))}
        </div>
      </aside>
    </div>
  );
}
