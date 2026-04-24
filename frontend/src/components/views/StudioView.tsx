import { TerminalButton } from "../primitives/TerminalButton";
import type { BuilderDraft } from "../../lib/app-model";
import type { CommandPreset, ExecutionTask, Follower, SignalSource } from "../../types";
import { StudioHeader } from "./studio/StudioHeader";
import {
  StudioActionSection,
  StudioActionTabs,
  StudioIdentitySection,
  StudioProductTabs,
  StudioRiskSection
} from "./studio/StudioFormSections";
import { StudioOutputs } from "./studio/StudioOutputs";
import { StudioLiveQueueTable, StudioPresetsTable } from "./studio/StudioTables";

type Props = {
  draft: BuilderDraft;
  onDraftChange: (draft: BuilderDraft) => void;
  commandOutput: string;
  executionOutput: string;
  instrumentOptions: Array<{ label: string; value: string }>;
  signals: SignalSource[];
  followers: Follower[];
  presets: CommandPreset[];
  recentExecutions: ExecutionTask[];
  selectedPresetId: string | null;
  locale: string;
  tr: (key: string) => string;
  onRefreshInstruments: () => void;
  onGenerate: () => void;
  onExecute: () => void;
  onCopyCommand: () => void;
  onPresetSelect: (presetId: string) => void;
  onOpenAudit: (taskId: string) => void;
};

export function StudioView(props: Props) {
  const { draft, tr } = props;
  const executeDisabled = !draft.symbol.trim() || !draft.account_id;

  return (
    <section className="panel studio-panel">
      <StudioHeader
        eyebrow={tr("studio")}
        title="Execution Studio"
        onRefreshInstruments={props.onRefreshInstruments}
        refreshLabel={tr("refresh")}
        exchange={draft.exchange}
        environment={draft.environment}
        productType={draft.product_type}
      />
      <StudioProductTabs draft={draft} onDraftChange={props.onDraftChange} />
      <div className="studio-grid">
        <div className="studio-main terminal-surface">
          <StudioIdentitySection
            draft={draft}
            onDraftChange={props.onDraftChange}
            signals={props.signals}
            followers={props.followers}
            instrumentOptions={props.instrumentOptions}
            tr={tr}
          />
          <StudioActionTabs draft={draft} onDraftChange={props.onDraftChange} />
          <StudioActionSection draft={draft} onDraftChange={props.onDraftChange} tr={tr} />
          <StudioRiskSection draft={draft} onDraftChange={props.onDraftChange} />
          <div className="builder-actions">
            <TerminalButton className="primary" type="button" onClick={props.onGenerate}>{tr("build")}</TerminalButton>
            <TerminalButton className="secondary" type="button" onClick={props.onCopyCommand}>Copy</TerminalButton>
            <TerminalButton className="secondary" type="button" onClick={props.onExecute} disabled={executeDisabled}>Execute</TerminalButton>
          </div>
          {executeDisabled ? <p className="field-hint">Execution requires a follower account and symbol. Empty symbol is blocked before the exchange call.</p> : null}
        </div>
        <StudioOutputs
          generatedTitle={tr("generatedCommand")}
          lastExecutionTitle={tr("lastExecution")}
          commandOutput={props.commandOutput}
          executionOutput={props.executionOutput}
        />
      </div>
      <div className="split-shell">
        <StudioPresetsTable
          presets={props.presets}
          signals={props.signals}
          selectedPresetId={props.selectedPresetId}
          locale={props.locale}
          exchangeLabel={tr("exchange")}
          signalLabel={tr("signal")}
          onPresetSelect={props.onPresetSelect}
        />
        <StudioLiveQueueTable
          executions={props.recentExecutions}
          title={tr("liveQueue")}
          signalLabel={tr("signal")}
          followerLabel={tr("follower")}
          symbolLabel={tr("symbol")}
          statusLabel={tr("status")}
          latencyLabel={tr("latency")}
          onOpenAudit={props.onOpenAudit}
        />
      </div>
    </section>
  );
}
