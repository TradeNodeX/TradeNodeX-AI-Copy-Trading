import type {
  CommandPreset,
  CopyTrade,
  DashboardResponse,
  ExecutionAudit,
  Follower,
  Instrument,
  ManualExecutionResponse,
  PositionSnapshot,
  SignalSource,
  TradeLogListResponse,
  ValidationResult
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  dashboard(displayCurrency: string) {
    return request<DashboardResponse>(`/v1/dashboard?display_currency=${encodeURIComponent(displayCurrency)}`);
  },
  positions(displayCurrency: string) {
    return request<PositionSnapshot[]>(`/v1/positions?display_currency=${encodeURIComponent(displayCurrency)}`);
  },
  logs(params: URLSearchParams) {
    return request<TradeLogListResponse>(`/v1/logs/query?${params.toString()}`);
  },
  instruments(exchange: string) {
    return request<Instrument[]>(`/v1/instruments?exchange=${encodeURIComponent(exchange)}`);
  },
  executionAudit(taskId: string) {
    return request<ExecutionAudit>(`/v1/executions/${taskId}/audit`);
  },
  createSignal(payload: Record<string, unknown>) {
    return request<SignalSource>("/v1/signal-sources", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  updateSignal(id: string, payload: Record<string, unknown>) {
    return request<SignalSource>(`/v1/signal-sources/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },
  validateSignal(id: string) {
    return request<ValidationResult>(`/v1/signal-sources/${id}/validate`, { method: "POST" });
  },
  deleteSignal(id: string) {
    return request<{ deleted: boolean; id: string }>(`/v1/signal-sources/${id}`, { method: "DELETE" });
  },
  createFollower(payload: Record<string, unknown>) {
    return request<Follower>("/v1/followers", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  updateFollower(id: string, payload: Record<string, unknown>) {
    return request<Follower>(`/v1/followers/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },
  validateFollower(id: string) {
    return request<Follower>(`/v1/followers/${id}/validate`, { method: "POST" });
  },
  pauseFollower(id: string) {
    return request<Follower>(`/v1/followers/${id}/pause`, { method: "POST" });
  },
  resumeFollower(id: string) {
    return request<Follower>(`/v1/followers/${id}/resume`, { method: "POST" });
  },
  deleteFollower(id: string) {
    return request<{ deleted: boolean; id: string }>(`/v1/followers/${id}`, { method: "DELETE" });
  },
  createCopyTrade(payload: Record<string, unknown>) {
    return request<CopyTrade>("/v1/copy-trades", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  updateCopyTrade(id: string, payload: Record<string, unknown>) {
    return request<CopyTrade>(`/v1/copy-trades/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },
  deleteCopyTrade(id: string) {
    return request<{ deleted: boolean; id: string }>(`/v1/copy-trades/${id}`, { method: "DELETE" });
  },
  generateCommand(payload: Record<string, unknown>) {
    return request<CommandPreset>("/v1/commands/generate", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },
  executeCommand(payload: Record<string, unknown>) {
    return request<ManualExecutionResponse>("/v1/commands/execute", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }
};
