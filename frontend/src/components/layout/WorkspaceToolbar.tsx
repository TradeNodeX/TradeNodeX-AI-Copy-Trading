import type { CurrencyOption, LanguageOption } from "../../config";
import type { Density, FontScale, MotionPref } from "../../lib/app-model";

type Props = {
  search: string;
  onSearchChange: (value: string) => void;
  language: string;
  languages: LanguageOption[];
  onLanguageChange: (value: string) => void;
  displayCurrency: string;
  currencies: CurrencyOption[];
  onCurrencyChange: (value: string) => void;
  density: Density;
  onDensityChange: (value: Density) => void;
  fontScale: FontScale;
  onFontScaleChange: (value: FontScale) => void;
  motionPref: MotionPref;
  onMotionChange: (value: MotionPref) => void;
  tr: (key: string) => string;
};

export function WorkspaceToolbar(props: Props) {
  return (
    <section className="toolbar-row">
      <div className="toolbar-search">
        <label>{props.tr("workspaceSearch")}</label>
        <div className="search-shell">
          <span className="search-icon">⌕</span>
          <input value={props.search} onChange={(event) => props.onSearchChange(event.target.value)} placeholder={props.tr("searchPlaceholder")} />
        </div>
      </div>
      <div className="toolbar-controls">
        <label>
          <span>{props.tr("language")}</span>
          <select value={props.language} onChange={(event) => props.onLanguageChange(event.target.value)}>
            {props.languages.map((item) => (
              <option key={item.code} value={item.code}>
                {item.label} · {item.tier}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>{props.tr("displayCurrency")}</span>
          <select value={props.displayCurrency} onChange={(event) => props.onCurrencyChange(event.target.value)}>
            {props.currencies.map((item) => (
              <option key={item.code} value={item.code}>
                {item.code} · {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>{props.tr("density")}</span>
          <select value={props.density} onChange={(event) => props.onDensityChange(event.target.value as Density)}>
            <option value="standard">{props.tr("standard")}</option>
            <option value="compact">{props.tr("compact")}</option>
          </select>
        </label>
        <label>
          <span>{props.tr("fontScale")}</span>
          <select value={props.fontScale} onChange={(event) => props.onFontScaleChange(event.target.value as FontScale)}>
            <option value="small">{props.tr("small")}</option>
            <option value="default">{props.tr("default")}</option>
            <option value="large">{props.tr("large")}</option>
          </select>
        </label>
        <label>
          <span>{props.tr("motion")}</span>
          <select value={props.motionPref} onChange={(event) => props.onMotionChange(event.target.value as MotionPref)}>
            <option value="full">{props.tr("full")}</option>
            <option value="reduced">{props.tr("reduced")}</option>
          </select>
        </label>
      </div>
    </section>
  );
}
