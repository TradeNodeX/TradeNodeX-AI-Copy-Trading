import { statusTone } from "../../lib/app-model";

export function StatusPill({ value }: { value: string | null | undefined }) {
  return <span className={`status-pill tone-${statusTone(value)}`}>{value ?? "--"}</span>;
}
