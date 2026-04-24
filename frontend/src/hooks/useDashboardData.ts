import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../api";
import { emptyDashboard } from "../lib/app-model";
import type { DashboardResponse, PositionSnapshot, TradeLogListResponse, WebsocketSnapshot } from "../types";

export type LogFilters = {
  page: number;
  limit: number;
  exchange: string;
  log_type: string;
  search: string;
  sort_by: string;
  sort_order: string;
};

const initialLogFilters: LogFilters = {
  page: 1,
  limit: 100,
  exchange: "",
  log_type: "",
  search: "",
  sort_by: "timestamp",
  sort_order: "desc"
};

export function useDashboardData(displayCurrency: string, builderExchange: string) {
  const [dashboard, setDashboard] = useState<DashboardResponse>(emptyDashboard());
  const [positions, setPositions] = useState<PositionSnapshot[]>([]);
  const [logsPage, setLogsPage] = useState<TradeLogListResponse>({ items: [], total: 0, page: 1, limit: 100, page_count: 1 });
  const [instrumentOptions, setInstrumentOptions] = useState<Array<{ label: string; value: string }>>([]);
  const [logFilters, setLogFilters] = useState<LogFilters>(initialLogFilters);
  const logFiltersRef = useRef<LogFilters>(initialLogFilters);

  useEffect(() => {
    logFiltersRef.current = logFilters;
  }, [logFilters]);

  const loadDashboard = useCallback(async () => {
    const next = await api.dashboard(displayCurrency);
    setDashboard(next);
    return next;
  }, [displayCurrency]);

  const loadPositions = useCallback(async () => {
    const next = await api.positions(displayCurrency);
    setPositions(next);
    return next;
  }, [displayCurrency]);

  const loadLogs = useCallback(async (nextFilters?: LogFilters) => {
    const filters = nextFilters ?? logFiltersRef.current;
    const params = new URLSearchParams();
    params.set("page", String(filters.page));
    params.set("limit", String(filters.limit));
    params.set("sort_by", filters.sort_by);
    params.set("sort_order", filters.sort_order);
    if (filters.exchange) params.set("exchange", filters.exchange);
    if (filters.log_type) params.set("log_type", filters.log_type);
    if (filters.search) params.set("search", filters.search);
    const page = await api.logs(params);
    setLogsPage(page);
    return page;
  }, []);

  const loadInstruments = useCallback(async (exchange: string) => {
    const payload = await api.instruments(exchange);
    const next = payload
      .map((item) => {
        const record = item as Record<string, unknown>;
        const symbol = String(record.symbol ?? record.instId ?? record.name ?? "");
        return { label: symbol || JSON.stringify(record), value: symbol };
      })
      .filter((item) => item.value)
      .slice(0, 200);
    setInstrumentOptions(next);
    return next;
  }, []);

  const applyRealtimeSnapshot = useCallback((payload: WebsocketSnapshot) => {
    setDashboard((prev) => ({
      ...prev,
      logs: payload.logs ?? prev.logs,
      recent_executions: payload.executions ?? prev.recent_executions,
      fx_meta: payload.fx_meta ?? prev.fx_meta,
      equity_summary: payload.equity_summary ?? prev.equity_summary,
      worker_status: payload.worker_status ?? prev.worker_status
    }));
  }, []);

  useEffect(() => {
    void Promise.all([loadDashboard(), loadPositions()]);
  }, [loadDashboard, loadPositions]);

  useEffect(() => {
    void loadLogs(logFilters);
  }, [logFilters, loadLogs]);

  useEffect(() => {
    void loadInstruments(builderExchange).catch(() => setInstrumentOptions([]));
  }, [builderExchange, loadInstruments]);

  return {
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
  };
}
