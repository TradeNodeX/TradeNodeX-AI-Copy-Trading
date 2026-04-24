import type { View } from "../../types";

type Props = {
  views: Array<{ id: View; label: string }>;
  activeView: View;
  onChange: (view: View) => void;
  tr: (key: string) => string;
};

export function ViewTabs({ views, activeView, onChange, tr }: Props) {
  return (
    <nav className="view-tabs">
      {views.map((view) => (
        <button key={view.id} className={activeView === view.id ? "is-active" : ""} onClick={() => onChange(view.id)} type="button">
          {tr(view.label)}
        </button>
      ))}
    </nav>
  );
}
