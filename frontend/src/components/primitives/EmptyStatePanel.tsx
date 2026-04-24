type Props = {
  title: string;
  description: string;
};

export function EmptyStatePanel({ title, description }: Props) {
  return (
    <div className="empty-state-panel terminal-surface">
      <div className="empty-state-kicker">{title}</div>
      <p>{description}</p>
    </div>
  );
}
