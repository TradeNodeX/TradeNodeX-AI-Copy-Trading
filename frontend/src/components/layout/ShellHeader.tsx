import type { CurrencyOption, LanguageOption } from "../../config";

type Props = {
  liveConnected: boolean;
  liveLatency: string;
  workerStatus?: string | null;
  language: string;
  languages: LanguageOption[];
  onLanguageChange: (value: string) => void;
  displayCurrency: string;
  currencies: CurrencyOption[];
  onCurrencyChange: (value: string) => void;
  tr: (key: string) => string;
};

export function ShellHeader({
  liveConnected,
  liveLatency,
  workerStatus,
  language,
  languages,
  onLanguageChange,
  displayCurrency,
  currencies,
  onCurrencyChange,
  tr
}: Props) {
  return (
    <header className="top-header">
      <div className="brand-cluster minimalist">
        <h1>TRADENODEX</h1>
      </div>
      <div className="header-status compact">
        <a className="ai-link" href="https://tradenodex.com">
          TradeNodeX AI
        </a>
        <div className="header-stat inline-stat">
          <span className="header-label">Connectivity</span>
          <strong className={liveConnected ? "tone-good" : "tone-warning"}>{liveLatency}</strong>
        </div>
        <div className="header-stat inline-stat">
          <span className="header-label">Realtime</span>
          <strong className={liveConnected ? "tone-good" : "tone-danger"}>{liveConnected ? tr("connected") : tr("offline")}</strong>
        </div>
        <div className="header-stat inline-stat">
          <span className="header-label">Worker</span>
          <strong className={workerStatus === "RUNNING" ? "tone-good" : workerStatus === "STALE" ? "tone-warning" : "tone-danger"}>{workerStatus ?? "OFFLINE"}</strong>
        </div>
        <div className="header-stat inline-stat">
          <span className="header-label">{tr("displayCurrency")}</span>
          <select
            aria-label={tr("displayCurrency")}
            className="header-select"
            value={displayCurrency}
            onChange={(event) => onCurrencyChange(event.target.value)}
          >
            {currencies.map((item) => (
              <option key={item.code} value={item.code}>
                {item.code} · {item.label}
              </option>
            ))}
          </select>
        </div>
        <div className="header-stat inline-stat">
          <span className="header-label">{tr("language")}</span>
          <select aria-label={tr("language")} className="header-select" value={language} onChange={(event) => onLanguageChange(event.target.value)}>
            {languages.map((item) => (
              <option key={item.code} value={item.code}>
                {item.label} · {item.tier}
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}
