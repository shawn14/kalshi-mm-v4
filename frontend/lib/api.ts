import type {
  MMState, ActiveOrder, InventoryItem, BacktestResult,
  PaperPerformance, SystemStatus, SeriesScore,
} from "@/types/trading";

// In static export, API calls go to the same host that served the page.
// FastAPI serves /api/* on the same port as the static files.
const BASE = typeof window !== "undefined"
  ? `${window.location.protocol}//${window.location.host}/api`
  : "/api";

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

export const api = {
  // MM
  mmState: () => get<MMState>("/mm/state"),
  mmQuotes: () => get<{ orders: ActiveOrder[] }>("/mm/quotes"),
  mmInventory: () => get<{ inventory: InventoryItem[] }>("/mm/inventory"),
  mmKill: () => post("/mm/kill"),
  mmResume: () => post("/mm/resume"),
  mmGoLive: (capital_usd: number) => post("/mm/go-live", { capital_usd }),
  mmGoPaper: () => post("/mm/go-paper"),

  // Research
  backtestResults: () => get<{ results: BacktestResult[] }>("/research/backtest"),
  runBacktest: () => post("/research/run-backtest"),
  paperPerformance: () => get<PaperPerformance>("/research/paper"),
  seriesScores: () => get<{ scores: SeriesScore[] }>("/research/series-scores"),

  // System
  systemStatus: () => get<SystemStatus>("/system/status"),
};
