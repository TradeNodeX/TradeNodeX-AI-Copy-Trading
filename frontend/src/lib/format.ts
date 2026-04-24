export function formatDisplay(value: string | number | null | undefined, locale: string, currency?: string): string {
  if (value === null || value === undefined || value === "") return "—";
  const numberValue = Number(value);
  if (Number.isFinite(numberValue)) {
    if (currency) {
      return new Intl.NumberFormat(locale, {
        style: "currency",
        currency,
        maximumFractionDigits: 2
      }).format(numberValue);
    }
    return new Intl.NumberFormat(locale, { maximumFractionDigits: 4 }).format(numberValue);
  }
  return String(value);
}

export function formatTimestamp(value: string | null | undefined, locale: string): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(date);
}
