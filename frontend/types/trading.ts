export type Side = "yes" | "no";
export type Mode = "paper" | "live";
export type Verdict = "PASS" | "FAIL" | "INSUFFICIENT";

export interface MMState {
  dry_run: boolean;
  kill: boolean;
  breaker_tripped: boolean;
  session_pnl_usd: number;
  capital_usd: number;
  active_orders: number;
  active_tickers: number;
  inventory: Record<string, { net_yes: number; pnl_c: number }>;
}

export interface ActiveOrder {
  ticker: string;
  side: Side;
  price_c: number;
  count: number;
  placed_at: string;
}

export interface InventoryItem {
  ticker: string;
  net_yes: number;
  fills_yes: number;
  fills_no: number;
  pnl_c: number;
}

export interface BacktestResult {
  series: string;
  n_markets: number;
  n_trades: number;
  win_rate: number;
  avg_ev_c: number;
  total_pnl_c: number;
  wilson_lb: number;
  wilson_lb_h1: number;
  wilson_lb_h2: number;
  verdict: Verdict;
  params: {
    half_spread_c: number;
    min_spread_c: number;
    mid_lo: number;
    mid_hi: number;
  };
}

export interface PaperPerformance {
  n: number;
  wins: number;
  win_rate: number;
  total_pnl_c: number;
  avg_pnl_c: number;
}

export interface SystemStatus {
  paper_mode: boolean;
  engine_running: boolean;
  kill_switch: boolean;
  circuit_breaker: boolean;
  ts: string;
}

export interface SeriesScore {
  series: string;
  avg_spread_c: number;
  pct_in_zone: number;
  ev_estimate: number;
  rank: number;
  notes: string;
}

export interface Fill {
  fill_id: string;
  ticker: string;
  series: string;
  side: Side;
  price_c: number;
  contracts: number;
  filled_at: string;
  result?: string;
  pnl_c?: number;
}
