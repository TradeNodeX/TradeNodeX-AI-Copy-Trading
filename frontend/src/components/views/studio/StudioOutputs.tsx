type Props = {
  generatedTitle: string;
  lastExecutionTitle: string;
  commandOutput: string;
  executionOutput: string;
};

export function StudioOutputs({ generatedTitle, lastExecutionTitle, commandOutput, executionOutput }: Props) {
  return (
    <div className="studio-side">
      <section className="studio-output terminal-surface">
        <div className="panel-inline-head"><h3>{generatedTitle}</h3></div>
        <textarea value={commandOutput} onChange={() => undefined} rows={12} readOnly />
      </section>
      <section className="studio-output terminal-surface">
        <div className="panel-inline-head"><h3>{lastExecutionTitle}</h3></div>
        <textarea value={executionOutput} onChange={() => undefined} rows={12} readOnly />
      </section>
    </div>
  );
}
