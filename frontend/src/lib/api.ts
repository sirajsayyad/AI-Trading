/**
 * API client for the AI Trading Platform backend.
 */

import { clearDashboardCache } from "./dashboard-cache";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

let refreshInFlight: Promise<boolean> | null = null;
async function refreshAccessToken(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const previous = localStorage.getItem("refresh_token");
      if (!previous) return false;
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: previous }), signal: AbortSignal.timeout(10000),
      });
      if (!response.ok) return false;
      const tokens = await response.json();
      // Do not revive a session that was logged out or replaced while refreshing.
      if (localStorage.getItem("refresh_token") !== previous) return !!localStorage.getItem("access_token");
      if (typeof tokens.access_token !== "string" || typeof tokens.refresh_token !== "string") return false;
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      return true;
    })().finally(() => { refreshInFlight = null; });
  }
  return refreshInFlight;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  timeoutMs?: number;
}

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {} } = options;

  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const payload = isForm ? body : body ? JSON.stringify(body) : undefined;
  const contentHeaders: Record<string, string> = isForm ? {} : { "Content-Type": "application/json" };
  const timeoutMs = options.timeoutMs ?? (endpoint.startsWith("/coach/") || endpoint.startsWith("/ai-coach/chat") || endpoint.endsWith("/coach") ? 210000 : 10000);
  const timeoutSignal = AbortSignal.timeout(timeoutMs);
  const requestSignal = options.signal ? AbortSignal.any([options.signal, timeoutSignal]) : timeoutSignal;
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  let res = await fetch(`${API_BASE}${endpoint}`, {
    method,
    headers: {
      ...contentHeaders,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    signal: requestSignal,
    body: payload,
  });

  if (res.status === 401 && endpoint !== "/auth/login" && typeof window !== "undefined") {
    const current = localStorage.getItem("access_token");
    const refreshed = current && current !== token ? true : await refreshAccessToken();
    const nextToken = localStorage.getItem("access_token");
    if (refreshed && nextToken) {
      res = await fetch(`${API_BASE}${endpoint}`, {
        method, headers: { ...contentHeaders, Authorization: `Bearer ${nextToken}`, ...headers },
        signal: requestSignal, body: payload,
      });
    }
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof error.detail === "string" ? error.detail : "The request was invalid. Check your message and try again.");
  }

  if (method !== "GET" && (endpoint === "/paper/orders" || endpoint === "/risk/profile")) clearDashboardCache();
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ─── Health ───────────────────────────────────────────────
export const api = {
  health: () => request<{ status: string }>("/health"),

  // ─── Auth ───────────────────────────────────────────────
  register: (email: string, username: string, password: string) =>
    request("/auth/register", { method: "POST", body: { email, username, password } }),

  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string; user: unknown }>(
      "/auth/login", { method: "POST", body: { email, password } }
    ),

  getMe: () => request("/auth/me"),

  getDashboardSummary: () => request<DashboardSummary>("/dashboard/summary"),
  getDashboardHistory: (range: DashboardRange) => request<DashboardHistory>(`/dashboard/history?range=${range}`),

  // ─── Market Data ────────────────────────────────────────
  getSymbols: () => request<Array<{ symbol: string; timeframes: string[]; first_date: string; last_date: string }>>("/data/symbols"),

  getCandles: (symbol: string, timeframe = "1D", start?: string, end?: string) => {
    const params = new URLSearchParams({ timeframe });
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    return request(`/data/${symbol}/candles?${params}`);
  },

  getLiveCandles: (symbol: string, timeframe = "1D", limit = 100) =>
    request<Array<{ symbol: string; timestamp: string; open: number; high: number; low: number; close: number; volume: number; timeframe: string; provider?: string; is_delayed?: boolean }>>(
      `/data/${encodeURIComponent(symbol)}/live-candles?timeframe=${timeframe}&limit=${limit}`
    ),

  getLiveQuote: (symbol: string) =>
    request<{ symbol: string; price: number; previous_close: number; change: number; percent_change: number; is_market_open: boolean; timestamp: string; provider: string; feed: string; is_delayed: boolean }>(
      `/data/${encodeURIComponent(symbol)}/live-quote`
    ),

  // ─── Backtesting ────────────────────────────────────────
  getStrategies: () => request<Array<{ name: string; params: Record<string, unknown> }>>("/backtest/strategies"),

  runBacktest: (config: {
    symbol: string;
    strategy_name: string;
    timeframe: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    strategy_params: Record<string, unknown>;
    stored_only?: boolean;
  }) => request("/backtest/run", { method: "POST", body: config }),

  getBacktest: (id: string) => request(`/backtest/${id}`),

  runWalkForward: (config: unknown) =>
    request("/backtest/walk-forward", { method: "POST", body: config }),

  runMonteCarlo: (config: unknown) =>
    request("/backtest/monte-carlo", { method: "POST", body: config }),

  // ─── Replay ─────────────────────────────────────────────
  createReplaySession: (config: {
    symbol: string;
    timeframe: string;
    start_date: string;
    speed_multiplier: number;
    blind_mode: boolean;
    stored_only?: boolean;
  }) => request("/replay/session", { method: "POST", body: config }),

  controlReplay: (sessionId: string, action: string, value?: string) =>
    request(`/replay/${sessionId}/control`, { method: "POST", body: { action, value } }),

  placeReplayOrder: (sessionId: string, order: { side: string; order_type: string; quantity: number; price?: number }) =>
    request(`/replay/${sessionId}/order`, { method: "POST", body: order }),

  getReplaySummary: (sessionId: string) => request(`/replay/${sessionId}/summary`),

  // ─── AI Coach ───────────────────────────────────────────
  getCritique: (trades: unknown[], sessionSummary?: unknown) =>
    request<{ feedback: string }>("/coach/critique", { method: "POST", body: { trades, session_summary: sessionSummary } }),

  askCoach: (question: string, tradeContext?: unknown[], history?: unknown[]) =>
    request<{ answer: string }>("/coach/ask", { method: "POST", body: { question, trade_context: tradeContext, conversation_history: history } }),

  analyzeBehavior: (trades: unknown[], accountSize = 100000) =>
    request<{ flags: unknown[] }>("/coach/behavior", { method: "POST", body: { trades, account_size: accountSize } }),

  reviewMyTrades: () => request<{ feedback: string; trade_count: number }>("/coach/review-my-trades", { method: "POST" }),

  getRiskProfile: () => request<RiskProfile>("/risk/profile"),
  updateRiskProfile: (profile: RiskProfile) => request<RiskProfile>("/risk/profile", { method: "PUT", body: profile }),
  previewPaperOrder: (order: PaperOrderInput) => request<OrderPreview>("/paper/orders/preview", { method: "POST", body: order }),
  submitPaperOrder: (order: PaperOrderInput) => request<{ id: string; status: string; errors?: string[] }>("/paper/orders", { method: "POST", body: order }),
  getPaperPortfolio: () => request<PaperPortfolio>("/paper/portfolio"),
  getWatchlist: () => request<Array<{ id: string; symbol: string }>>("/watchlist"),
  addWatchlist: (symbol: string) => request(`/watchlist/${encodeURIComponent(symbol)}`, { method: "POST" }),
  removeWatchlist: (symbol: string) => request(`/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" }),
  getJournal: (page = 1, pageSize = 20) => request<JournalEntry[]>(`/journal?page=${page}&page_size=${pageSize}`),
  createJournal: (entry: JournalInput) => request<JournalEntry>("/journal", { method: "POST", body: entry }),
  deleteJournal: (id: string) => request(`/journal/${id}`, { method: "DELETE" }),

  // ─── Curriculum ─────────────────────────────────────────
  getCourses: () => request<Array<{ id: string; title: string; description: string; difficulty: string }>>("/courses"),

  getCourse: (id: string) => request(`/courses/${id}`),

  getLesson: (id: string) => request(`/lessons/${id}`),
};

export type RiskProfile = {
  starting_balance: number; max_risk_percent: number; max_daily_loss_percent: number;
  max_open_positions: number; max_position_value_percent: number;
  min_reward_risk_ratio: number; require_stop_loss: boolean; timezone: string;
  trading_session: "regular" | "extended" | "any"; cooldown_after_losses: number;
};
export type PaperOrderInput = {
  symbol: string; side: "buy" | "sell"; order_type: "market" | "limit" | "stop";
  quantity: number; limit_price?: number; stop_price?: number;
  take_profit_price?: number; idempotency_key: string;
};
export type OrderPreview = {
  allowed: boolean; errors: string[]; market_price: number; position_value: number;
  risk_amount: number; risk_percent: number; potential_reward: number;
  reward_risk_ratio: number; estimated_commission: number; estimated_slippage: number;
  buying_power_after: number; provider: string; data_timestamp: string; paper_only: boolean;
};
export type PaperPortfolio = {
  cash: number; buying_power: number; market_value: number; equity: number;
  realized_pnl: number; unrealized_pnl: number; total_fees: number; paper_only: boolean;
  positions: Array<{ id: string; symbol: string; quantity: number; avg_entry_price: number; mark_price: number; unrealized_pnl: number; stop_price?: number; take_profit_price?: number }>;
  orders: Array<{ id: string; symbol: string; side: string; quantity: number; status: string; fill_price?: number; created_at: string }>;
};
export type JournalInput = {
  trade_id?: string; symbol: string; strategy: string; setup: string; entry_reason: string;
  exit_reason: string; stop_price?: number; target_price?: number; confidence: number;
  emotion_before: string; emotion_during: string; emotion_after: string;
  mistakes: string; lessons_learned: string; review: string; screenshot_url?: string; tags: string[];
};
export type JournalEntry = JournalInput & { id: string; created_at: string; updated_at: string };
export type DashboardSummary = {
  equity: number | null; cash: number | null; realized_pnl: number | null; total_trades: number; win_rate: number;
  profit_factor: number | null; expectancy: number; average_win: number; average_loss: number;
  current_streak: number; risk_violations: number; open_positions: number;
  best_symbol: string | null; worst_symbol: string | null; learning_progress: number; paper_only: boolean;
  recent_trades: Array<{ id: string; symbol: string; timestamp: string; realized_pnl: number }>;
  risk: { exposure: number | null; daily_pnl: number; daily_loss_limit: number | null; daily_loss_used_percent: number | null };
};
export type DashboardRange = "7D" | "30D" | "All";
export type DashboardHistory = { points: Array<{ timestamp: string; equity: number; drawdown: number }>; observation_count: number; max_drawdown: number | null };

export function getWsUrl(sessionId: string): string {
  return getSocketUrl(`/replay/${sessionId}/stream`);
}

export function getMarketWsUrl(symbol: string): string {
  return getSocketUrl(`/data/stream/${encodeURIComponent(symbol)}`);
}

function getSocketUrl(path: string): string {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}
