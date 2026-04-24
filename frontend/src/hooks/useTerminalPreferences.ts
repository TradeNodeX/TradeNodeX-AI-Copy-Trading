import { useCallback, useEffect, useMemo, useState } from "react";

import { currencies, getLanguage, languages, t } from "../config";
import type { Density, FontScale, MotionPref } from "../lib/app-model";

export function useTerminalPreferences() {
  const [language, setLanguage] = useState(localStorage.getItem("tnx-language") || "en");
  const [displayCurrency, setDisplayCurrency] = useState(localStorage.getItem("tnx-currency") || "USD");
  const [density, setDensity] = useState<Density>((localStorage.getItem("tnx-density") as Density) || "standard");
  const [fontScale, setFontScale] = useState<FontScale>((localStorage.getItem("tnx-font-scale") as FontScale) || "default");
  const [motionPref, setMotionPref] = useState<MotionPref>((localStorage.getItem("tnx-motion") as MotionPref) || "full");

  const languageMeta = useMemo(() => getLanguage(language), [language]);
  const locale = languageMeta.locale;
  const tr = useCallback((key: string) => t(language, key), [language]);

  useEffect(() => {
    localStorage.setItem("tnx-language", language);
    document.documentElement.lang = languageMeta.locale;
    document.documentElement.dir = languageMeta.rtl ? "rtl" : "ltr";
  }, [language, languageMeta]);

  useEffect(() => localStorage.setItem("tnx-currency", displayCurrency), [displayCurrency]);
  useEffect(() => localStorage.setItem("tnx-density", density), [density]);
  useEffect(() => localStorage.setItem("tnx-font-scale", fontScale), [fontScale]);
  useEffect(() => localStorage.setItem("tnx-motion", motionPref), [motionPref]);

  return {
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
  };
}
