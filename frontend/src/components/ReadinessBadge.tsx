import type { ValidationStatus } from "../types";
import { statusTone } from "../lib/app-model";

export function ReadinessBadge({ label, status }: { label: string; status: ValidationStatus | string }) {
  return <span className={`readiness-pill tone-${statusTone(status)}`}>{label}: {status}</span>;
}
