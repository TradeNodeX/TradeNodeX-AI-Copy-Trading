import type { ReactNode } from "react";

type Props = {
  eyebrow: string;
  title: string;
  actions?: ReactNode;
};

export function SectionHeader({ eyebrow, title, actions }: Props) {
  return (
    <div className="section-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {actions ? <div className="section-actions">{actions}</div> : null}
    </div>
  );
}
