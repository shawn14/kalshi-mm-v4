"use client";
import { useMMState, useMMInventory, useSystemStatus } from "@/hooks/usePolling";
import { SectionHeader, StatRow } from "@/components/trading/StatRow";
import { cn } from "@/lib/utils";

function GaugeBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min(value / max * 100, 100);
  const isHigh = pct > 75;
  return (
    <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-surface2">
      <div
        className={cn("h-full rounded-full transition-all", isHigh ? "bg-red" : color)}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function RiskPage() {
  const { data: state } = useMMState();
  const { data: invData } = useMMInventory();
  const { data: sys } = useSystemStatus();

  const inventory = invData?.inventory ?? [];
  const totalExposure = inventory.reduce((s, i) => s + Math.abs(i.net_yes) * 0.50, 0);
  const maxExposure = (state?.capital_usd ?? 1000) * 0.50;
  const dailyLoss = -(state?.session_pnl_usd ?? 0);
  const maxDailyLoss = (state?.capital_usd ?? 1000) * 0.10;

  return (
    <div className="max-w-2xl px-4 pb-10 pt-6">
      {/* Circuit breaker / kill status */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className={cn(
          "flex flex-col gap-1 rounded-xl border p-4",
          sys?.circuit_breaker ? "border-red/40 bg-red/10" : "border-border bg-surface"
        )}>
          <span className="text-2xs uppercase tracking-widest text-muted-fg">Circuit Breaker</span>
          <span className={cn("text-lg font-bold", sys?.circuit_breaker ? "text-red" : "text-green")}>
            {sys?.circuit_breaker ? "TRIPPED" : "OK"}
          </span>
        </div>
        <div className={cn(
          "flex flex-col gap-1 rounded-xl border p-4",
          sys?.kill_switch ? "border-red/40 bg-red/10" : "border-border bg-surface"
        )}>
          <span className="text-2xs uppercase tracking-widest text-muted-fg">Kill Switch</span>
          <span className={cn("text-lg font-bold", sys?.kill_switch ? "text-red" : "text-green")}>
            {sys?.kill_switch ? "ACTIVE" : "Clear"}
          </span>
        </div>
      </div>

      {/* Exposure gauge */}
      <div className="mb-4 rounded-xl border border-border bg-surface p-4">
        <SectionHeader title="Exposure" />
        <div className="mb-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-fg-3">Total at risk</span>
            <span className="font-mono font-bold tabular">
              ${totalExposure.toFixed(2)}
              <span className="ml-1 text-xs text-muted-fg">/ ${maxExposure.toFixed(0)}</span>
            </span>
          </div>
          <GaugeBar value={totalExposure} max={maxExposure} color="bg-blue" />
        </div>
        <div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-fg-3">Daily loss</span>
            <span className={cn("font-mono font-bold tabular", dailyLoss > 0 ? "text-red" : "text-green")}>
              ${dailyLoss.toFixed(2)}
              <span className="ml-1 text-xs text-muted-fg">/ ${maxDailyLoss.toFixed(0)} limit</span>
            </span>
          </div>
          <GaugeBar value={Math.max(0, dailyLoss)} max={maxDailyLoss} color="bg-orange" />
        </div>
      </div>

      {/* Per-ticker breakdown */}
      {inventory.length > 0 && (
        <div className="rounded-xl border border-border bg-surface">
          <div className="border-b border-border px-4 py-3">
            <h2 className="text-2xs font-semibold uppercase tracking-widest text-muted-fg">
              Position Breakdown
            </h2>
          </div>
          <div className="divide-y divide-border/50">
            {inventory.map((item) => (
              <div key={item.ticker} className="px-4 py-3">
                <div className="flex items-center justify-between">
                  <span className="max-w-[220px] truncate font-mono text-xs text-fg-2">{item.ticker}</span>
                  <div className="flex items-center gap-4 text-xs">
                    <span className="text-muted-fg">YES fills: <span className="text-fg">{item.fills_yes}</span></span>
                    <span className="text-muted-fg">NO fills: <span className="text-fg">{item.fills_no}</span></span>
                    <span className={cn("font-mono font-bold tabular", item.net_yes >= 0 ? "text-green" : "text-red")}>
                      {item.net_yes > 0 ? "+" : ""}{item.net_yes} net
                    </span>
                  </div>
                </div>
                <div className="mt-1 flex items-center justify-between text-xs text-muted-fg">
                  <span>Realized P&L</span>
                  <span className={cn("font-mono tabular", item.pnl_c >= 0 ? "text-green" : "text-red")}>
                    {item.pnl_c >= 0 ? "+" : ""}{item.pnl_c.toFixed(1)}¢
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {inventory.length === 0 && (
        <div className="rounded-xl border border-border bg-surface p-8 text-center text-sm text-muted-fg">
          No open positions
        </div>
      )}
    </div>
  );
}
