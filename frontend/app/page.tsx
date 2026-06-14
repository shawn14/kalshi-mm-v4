"use client";
import { useMMState, useMMQuotes, useMMInventory, useSystemStatus } from "@/hooks/usePolling";
import { PnLChart } from "@/components/charts/PnLChart";
import { QuoteRow } from "@/components/trading/QuoteRow";
import { StatRow, SectionHeader } from "@/components/trading/StatRow";
import { cn } from "@/lib/utils";
import { useMemo, useRef } from "react";

function PnLValue({ usd }: { usd: number }) {
  return (
    <span className={cn("text-3xl font-bold tabular", usd >= 0 ? "text-green" : "text-red")}>
      {usd >= 0 ? "+" : ""}${Math.abs(usd).toFixed(2)}
    </span>
  );
}

function MiniStat({ label, value, valueClass }: { label: string; value: string | number; valueClass?: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-xl border border-border bg-surface p-3">
      <span className={cn("text-lg font-bold tabular", valueClass ?? "text-fg")}>{value}</span>
      <span className="text-2xs uppercase tracking-widest text-muted-fg">{label}</span>
    </div>
  );
}

function InventoryBar({ netYes, max = 10 }: { netYes: number; max?: number }) {
  const pct = Math.min(Math.abs(netYes) / max * 100, 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface2">
        <div
          className={cn("h-full rounded-full transition-all", netYes >= 0 ? "bg-green" : "bg-red")}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn("w-10 text-right text-xs font-semibold tabular", netYes >= 0 ? "text-green" : "text-red")}>
        {netYes > 0 ? "+" : ""}{netYes}
      </span>
    </div>
  );
}

export default function LivePage() {
  const { data: state } = useMMState();
  const { data: quotes } = useMMQuotes();
  const { data: inv } = useMMInventory();
  const { data: sys } = useSystemStatus();

  // Build a fake P&L chart history from session pnl (real impl uses event log)
  const pnlHistory = useMemo(() => {
    const pnl = state?.session_pnl_usd ?? 0;
    return [{ time: "start", pnl: 0 }, { time: "now", pnl }];
  }, [state?.session_pnl_usd]);

  const orders = quotes?.orders ?? [];
  const inventory = inv?.inventory ?? [];
  const pnl = state?.session_pnl_usd ?? 0;
  const isKilled = sys?.kill_switch;
  const isCB = sys?.circuit_breaker;

  return (
    <div className="max-w-2xl px-4 pb-10 pt-6">
      {/* Alert banner */}
      {(isKilled || isCB) && (
        <div className={cn(
          "mb-4 flex items-center gap-3 rounded-xl border px-4 py-3 text-sm font-semibold",
          isKilled ? "border-red/30 bg-red/10 text-red" : "border-orange/30 bg-orange/10 text-orange"
        )}>
          <span className="h-2 w-2 rounded-full bg-current animate-pulse" />
          {isKilled ? "KILL SWITCH ACTIVE — all quotes cancelled" : "CIRCUIT BREAKER TRIPPED — trading halted"}
        </div>
      )}

      {/* P&L Hero */}
      <div className="mb-4 rounded-xl border border-border bg-surface p-4">
        <p className="mb-1 text-2xs font-semibold uppercase tracking-widest text-muted-fg">Session P&L</p>
        <PnLValue usd={pnl} />
        <div className="mt-3">
          <PnLChart data={pnlHistory} height={80} />
        </div>
      </div>

      {/* Stats grid */}
      <div className="mb-4 grid grid-cols-3 gap-2">
        <MiniStat label="Orders" value={state?.active_orders ?? "—"} valueClass="text-blue" />
        <MiniStat label="Tickers" value={state?.active_tickers ?? "—"} />
        <MiniStat
          label="Capital"
          value={state?.capital_usd != null ? `$${state.capital_usd.toFixed(0)}` : "—"}
        />
      </div>

      {/* Active Quotes */}
      <div className="mb-4 rounded-xl border border-border bg-surface p-4">
        <SectionHeader title={`Active Quotes (${orders.length})`} />
        {orders.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-fg">No active quotes</p>
        ) : (
          <div className="max-h-64 overflow-y-auto">
            {orders.map((o, i) => <QuoteRow key={i} order={o} />)}
          </div>
        )}
      </div>

      {/* Inventory */}
      {inventory.length > 0 && (
        <div className="rounded-xl border border-border bg-surface p-4">
          <SectionHeader title="Book Inventory" />
          <div className="space-y-3">
            {inventory.map((item) => (
              <div key={item.ticker}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="max-w-[200px] truncate font-mono text-xs text-fg-2">{item.ticker}</span>
                  <span className={cn("font-mono text-xs font-semibold tabular", item.pnl_c >= 0 ? "text-green" : "text-red")}>
                    {item.pnl_c >= 0 ? "+" : ""}{item.pnl_c.toFixed(1)}¢
                  </span>
                </div>
                <InventoryBar netYes={item.net_yes} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
