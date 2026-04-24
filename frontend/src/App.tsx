import { useState } from "react";

import { api } from "./api";
import { AuditDrawer } from "./components/overlays/AuditDrawer";
import { FollowerModal } from "./components/overlays/FollowerModal";
import { SignalModal } from "./components/overlays/SignalModal";
import { MetricsShell } from "./components/layout/MetricsShell";
import { ShellHeader } from "./components/layout/ShellHeader";
import { ViewTabs } from "./components/layout/ViewTabs";
import { ApiRegistryView } from "./components/views/ApiRegistryView";
import { AuditLogsView } from "./components/views/AuditLogsView";
import { CopyTradesView } from "./components/views/CopyTradesView";
import { PositionsView } from "./components/views/PositionsView";
import { SignalsView } from "./components/views/SignalsView";
import { StudioView } from "./components/views/StudioView";
import { useCopyTradeEditor } from "./hooks/useCopyTradeEditor";
import { useDashboardData } from "./hooks/useDashboardData";
import { useRealtimeStream } from "./hooks/useRealtimeStream";
import { useTerminalPreferences } from "./hooks/useTerminalPreferences";
import {
  buildCommandPayload,
  initialBuilderDraft,
  initialFollowerDraft,
  initialSignalDraft,
  type BuilderDraft,
  type FollowerDraft,
  type SignalDraft,
  viewOrder
} from "./lib/app-model";
import type { ExecutionAudit, TradeLog, View } from "./types";

export default function App() {
  const [activeView, setActiveView] = useState<View>("SIGNALS");
  const {
    language,
    setLanguage,
    displayCurrency,
    setDisplayCurrency,
    density,
    setDensity,
    fontScale,
    setFontScale,
    motionPref,
    setMotionPref,
    languageMeta,
    locale,
    tr,
    languages,
    currencies
  } = useTerminalPreferences();
  const [signalDraft, setSignalDraft] = useState<SignalDraft>(initialSignalDraft());
  const [followerDraft, setFollowerDraft] = useState<FollowerDraft>(initialFollowerDraft());
  const [builderDraft, setBuilderDraft] = useState<BuilderDraft>(initialBuilderDraft());
  const [signalModalOpen, setSignalModalOpen] = useState(false);
  const [followerModalOpen, setFollowerModalOpen] = useState(false);
  const [selectedLog, setSelectedLog] = useState<TradeLog | null>(null);
  const [selectedAudit, setSelectedAudit] = useState<ExecutionAudit | null>(null);
  const [statusMessage, setStatusMessage] = useState("TradeNodeX React shell connected.");
  const [commandOutput, setCommandOutput] = useState("");
  const [executionOutput, setExecutionOutput] = useState("");
  const [selectedPresetId, setSelectedPresetId] = useState<string | null>(null);

  const {
    dashboard,
    positions,
    logsPage,
    instrumentOptions,
    logFilters,
    setLogFilters,
    loadDashboard,
    loadPositions,
    loadLogs,
    loadInstruments,
    applyRealtimeSnapshot
  } = useDashboardData(displayCurrency, builderDraft.exchange);
  const {
    selectedCopyTrade,
    selectedCopyTradeId,
    setSelectedCopyTradeId,
    copyTradeDraft,
    setCopyTradeDraft,
    resetCopyTradeEditor
  } = useCopyTradeEditor(dashboard.copy_trades);
  const { liveConnected, liveLatency } = useRealtimeStream(applyRealtimeSnapshot);
  const signalId = signalDraft.id;
  const followerId = followerDraft.id;

  async function handleSignalSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = {
      name: signalDraft.name,
      exchange: signalDraft.exchange,
      environment: signalDraft.environment,
      source_account: signalDraft.source_account,
      description: signalDraft.description || null,
      pairs_scope: signalDraft.pairs_scope,
      default_copy_mode: signalDraft.default_copy_mode,
      default_scale_factor: signalDraft.default_scale_factor,
      default_leverage: signalDraft.default_leverage ? Number(signalDraft.default_leverage) : null,
      margin_mode: signalDraft.margin_mode,
      hedge_mode: signalDraft.hedge_mode,
      broadcast_trade_enabled: signalDraft.broadcast_trade_enabled,
      api_key: signalDraft.api_key || null,
      api_secret: signalDraft.api_secret || null,
      api_passphrase: signalDraft.api_passphrase || null
    };

    if (signalDraft.id) {
      await api.updateSignal(signalDraft.id, payload);
      setStatusMessage(`Signal ${signalDraft.name} updated.`);
    } else {
      await api.createSignal(payload);
      setStatusMessage(`Signal ${signalDraft.name} created.`);
    }

    setSignalModalOpen(false);
    setSignalDraft(initialSignalDraft());
    const next = await loadDashboard();
    setStatusMessage(`Dashboard synced with ${next.signal_sources.length} signal sources and ${next.copy_trades.length} routes.`);
  }

  async function handleFollowerSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = {
      name: followerDraft.name,
      exchange: followerDraft.exchange,
      environment: followerDraft.environment,
      account_group: followerDraft.account_group,
      scale_factor: followerDraft.scale_factor,
      exact_copy_mode: followerDraft.exact_copy_mode,
      leverage: followerDraft.leverage ? Number(followerDraft.leverage) : null,
      margin_mode: followerDraft.margin_mode,
      hedge_mode: followerDraft.hedge_mode,
      api_key: followerDraft.api_key || null,
      api_secret: followerDraft.api_secret || null,
      api_passphrase: followerDraft.api_passphrase || null
    };

    if (followerDraft.id) {
      await api.updateFollower(followerDraft.id, payload);
      setStatusMessage(`API account ${followerDraft.name} updated.`);
    } else {
      await api.createFollower(payload);
      setStatusMessage(`API account ${followerDraft.name} created.`);
    }

    setFollowerModalOpen(false);
    setFollowerDraft(initialFollowerDraft());
    await loadDashboard();
  }

  async function handleCopyTradeSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const payload = {
      name: copyTradeDraft.name,
      signal_source_id: copyTradeDraft.signal_source_id,
      follower_account_id: copyTradeDraft.follower_account_id,
      copy_mode: copyTradeDraft.copy_mode,
      scale_factor: copyTradeDraft.scale_factor,
      override_leverage: copyTradeDraft.override_leverage ? Number(copyTradeDraft.override_leverage) : null,
      command_template: copyTradeDraft.command_template || null,
      notes: copyTradeDraft.notes || null,
      enabled: copyTradeDraft.enabled
    };

    if (copyTradeDraft.id) {
      await api.updateCopyTrade(copyTradeDraft.id, payload);
      setStatusMessage(`Copy trade ${copyTradeDraft.name} updated.`);
    } else {
      await api.createCopyTrade(payload);
      setStatusMessage(`Copy trade ${copyTradeDraft.name} created.`);
    }

    await loadDashboard();
  }

  async function handleGenerateCommand() {
    const preset = await api.generateCommand(buildCommandPayload(builderDraft));
    setCommandOutput(preset.raw_command);
    setSelectedPresetId(preset.id);
    setStatusMessage(`Preset ${preset.name} generated.`);
    await loadDashboard();
  }

  async function handleExecuteCommand() {
    if (!builderDraft.symbol.trim()) {
      setStatusMessage("Execution blocked: Symbol is required.");
      setExecutionOutput(JSON.stringify({ accepted: false, error: "Symbol is required for execution." }, null, 2));
      return;
    }
    const result = await api.executeCommand(buildCommandPayload(builderDraft));
    setExecutionOutput(JSON.stringify(result.result, null, 2));
    setStatusMessage(result.accepted ? "Manual execution accepted." : "Manual execution rejected.");
    await loadDashboard();
    await loadLogs({ ...logFilters, page: 1 });
  }

  async function openAudit(taskId: string) {
    setSelectedAudit(await api.executionAudit(taskId));
  }

  return (
    <div className={`terminal-root density-${density} scale-${fontScale} motion-${motionPref}`} dir={languageMeta.rtl ? "rtl" : "ltr"}>
      <ShellHeader
        liveConnected={liveConnected}
        liveLatency={liveLatency}
        workerStatus={dashboard.worker_status?.status ?? null}
        language={language}
        languages={languages}
        onLanguageChange={setLanguage}
        displayCurrency={displayCurrency}
        currencies={currencies}
        onCurrencyChange={setDisplayCurrency}
        tr={tr}
      />
      <MetricsShell
        runtimeMetrics={dashboard.runtime_metrics}
        performanceMetrics={dashboard.performance_metrics}
        equitySummary={dashboard.equity_summary}
        fxMeta={dashboard.fx_meta}
        tr={tr}
      />
      <section className="nav-status-row">
        <ViewTabs views={viewOrder} activeView={activeView} onChange={setActiveView} tr={tr} />
        <span className="status-banner-main">{statusMessage}</span>
      </section>
      <main className="workspace">
        {activeView === "SIGNALS" ? (
          <SignalsView
            signals={dashboard.signal_sources}
            tr={tr}
            onRefresh={() => void loadDashboard()}
            onCreate={() => { setSignalDraft(initialSignalDraft()); setSignalModalOpen(true); }}
            onEdit={(signal) => {
              setSignalDraft({
                id: signal.id,
                name: signal.name,
                exchange: signal.exchange,
                environment: signal.environment,
                source_account: signal.source_account,
                description: signal.description ?? "",
                pairs_scope: signal.pairs_scope,
                default_copy_mode: signal.default_copy_mode,
                default_scale_factor: signal.default_scale_factor,
                default_leverage: signal.default_leverage ? String(signal.default_leverage) : "",
                margin_mode: signal.margin_mode,
                hedge_mode: signal.hedge_mode,
                broadcast_trade_enabled: signal.broadcast_trade_enabled,
                api_key: "",
                api_secret: "",
                api_passphrase: ""
              });
              setSignalModalOpen(true);
            }}
            onValidate={(signalId) => void api.validateSignal(signalId).then(async (result) => {
              setStatusMessage(result.message ?? "Signal validation completed.");
              await loadDashboard();
            })}
            onBuild={(signal) => {
              setBuilderDraft((prev) => ({ ...prev, signal_source_id: signal.id, exchange: signal.exchange, environment: signal.environment }));
              setActiveView("EXECUTION_STUDIO");
            }}
          />
        ) : null}
        {activeView === "COPY_TRADES" ? (
          <CopyTradesView
            copyTrades={dashboard.copy_trades}
            followers={dashboard.followers}
            signals={dashboard.signal_sources}
            selectedCopyTrade={selectedCopyTrade}
            draft={copyTradeDraft}
            tr={tr}
            onRefresh={() => void loadDashboard()}
            onCreate={resetCopyTradeEditor}
            onSelect={setSelectedCopyTradeId}
            onDraftChange={setCopyTradeDraft}
            onSubmit={(event) => void handleCopyTradeSubmit(event)}
            onDelete={() => {
              if (!copyTradeDraft.id) return;
              void api.deleteCopyTrade(copyTradeDraft.id).then(async () => {
                resetCopyTradeEditor();
                await loadDashboard();
              });
            }}
          />
        ) : null}
        {activeView === "MANAGE_SIGNALS" ? (
          <ApiRegistryView
            signals={dashboard.signal_sources}
            followers={dashboard.followers}
            tr={tr}
            onRefresh={() => void loadDashboard()}
            onCreateSignal={() => { setSignalDraft(initialSignalDraft()); setSignalModalOpen(true); }}
            onCreateFollower={() => { setFollowerDraft(initialFollowerDraft()); setFollowerModalOpen(true); }}
            onEditSignal={(signal) => {
              setSignalDraft({
                id: signal.id,
                name: signal.name,
                exchange: signal.exchange,
                environment: signal.environment,
                source_account: signal.source_account,
                description: signal.description ?? "",
                pairs_scope: signal.pairs_scope,
                default_copy_mode: signal.default_copy_mode,
                default_scale_factor: signal.default_scale_factor,
                default_leverage: signal.default_leverage ? String(signal.default_leverage) : "",
                margin_mode: signal.margin_mode,
                hedge_mode: signal.hedge_mode,
                broadcast_trade_enabled: signal.broadcast_trade_enabled,
                api_key: "",
                api_secret: "",
                api_passphrase: ""
              });
              setSignalModalOpen(true);
            }}
            onValidateSignal={(id) => void api.validateSignal(id).then(async (result) => { setStatusMessage(result.message ?? "Validation completed."); await loadDashboard(); })}
            onEditFollower={(follower) => {
              setFollowerDraft({
                id: follower.id,
                name: follower.name,
                exchange: follower.exchange,
                environment: follower.environment,
                account_group: follower.account_group,
                scale_factor: follower.scale_factor,
                exact_copy_mode: follower.exact_copy_mode,
                leverage: follower.leverage ? String(follower.leverage) : "",
                margin_mode: follower.margin_mode,
                hedge_mode: follower.hedge_mode,
                api_key: "",
                api_secret: "",
                api_passphrase: ""
              });
              setFollowerModalOpen(true);
            }}
            onValidateFollower={(id) => void api.validateFollower(id).then(async (follower) => { setStatusMessage(follower.validation_message ?? "Validation completed."); await loadDashboard(); })}
            onToggleFollowerStatus={(follower) => void (follower.status === "ACTIVE" ? api.pauseFollower(follower.id) : api.resumeFollower(follower.id)).then(() => loadDashboard())}
          />
        ) : null}
        {activeView === "EXECUTION_STUDIO" ? (
          <StudioView
            draft={builderDraft}
            onDraftChange={setBuilderDraft}
            commandOutput={commandOutput}
            executionOutput={executionOutput}
            instrumentOptions={instrumentOptions}
            signals={dashboard.signal_sources}
            followers={dashboard.followers}
            presets={dashboard.command_presets}
            recentExecutions={dashboard.recent_executions}
            selectedPresetId={selectedPresetId}
            locale={locale}
            tr={tr}
            onRefreshInstruments={() => void loadInstruments(builderDraft.exchange).catch((error) => {
              setStatusMessage(error instanceof Error ? error.message : "Failed to load instruments.");
            })}
            onGenerate={() => void handleGenerateCommand()}
            onExecute={() => void handleExecuteCommand()}
            onCopyCommand={() => void navigator.clipboard.writeText(commandOutput)}
            onPresetSelect={(presetId) => {
              const preset = dashboard.command_presets.find((item) => item.id === presetId);
              setSelectedPresetId(presetId);
              if (preset) setCommandOutput(preset.raw_command);
            }}
            onOpenAudit={(taskId) => void openAudit(taskId)}
          />
        ) : null}
        {activeView === "TRADE_LOGS" ? (
          <AuditLogsView
            logsPage={logsPage}
            selectedLog={selectedLog}
            logFilters={logFilters}
            locale={locale}
            tr={tr}
            onRefresh={() => void loadLogs()}
            onLogFiltersChange={setLogFilters}
            onApply={(filters) => void loadLogs(filters ?? logFilters)}
            onSelectLog={setSelectedLog}
            onOpenAudit={(taskId) => void openAudit(taskId)}
          />
        ) : null}
        {activeView === "POSITIONS" ? (
          <PositionsView
            positions={positions}
            equitySummary={dashboard.equity_summary}
            displayCurrency={displayCurrency}
            locale={locale}
            tr={tr}
            onRefresh={() => void loadPositions()}
          />
        ) : null}
      </main>

      <AuditDrawer audit={selectedAudit} locale={locale} onClose={() => setSelectedAudit(null)} />
      <SignalModal
        open={signalModalOpen}
        draft={signalDraft}
        tr={tr}
        onClose={() => setSignalModalOpen(false)}
        onDraftChange={setSignalDraft}
        onSubmit={(event) => void handleSignalSubmit(event)}
        onValidate={signalId ? () => void api.validateSignal(signalId).then(async (result) => { setStatusMessage(result.message ?? "Validation completed."); await loadDashboard(); }) : undefined}
        onDelete={signalId ? () => void api.deleteSignal(signalId).then(async () => {
          setSignalModalOpen(false);
          setSignalDraft(initialSignalDraft());
          await loadDashboard();
        }) : undefined}
      />
      <FollowerModal
        open={followerModalOpen}
        draft={followerDraft}
        tr={tr}
        onClose={() => setFollowerModalOpen(false)}
        onDraftChange={setFollowerDraft}
        onSubmit={(event) => void handleFollowerSubmit(event)}
        onValidate={followerId ? () => void api.validateFollower(followerId).then(async (follower) => { setStatusMessage(follower.validation_message ?? "Validation completed."); await loadDashboard(); }) : undefined}
        onDelete={followerId ? () => void api.deleteFollower(followerId).then(async () => {
          setFollowerModalOpen(false);
          setFollowerDraft(initialFollowerDraft());
          await loadDashboard();
        }) : undefined}
      />

      <footer className="terminal-footer">
        <div>Binance, Bybit, OKX, Coinbase, Kraken, BitMEX, and Gate.io names are used only to describe exchange connectivity targets.</div>
        <div>TradeNodeX.com</div>
      </footer>
    </div>
  );
}
