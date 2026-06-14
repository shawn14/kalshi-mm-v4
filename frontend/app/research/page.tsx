"use client";
import { useBacktestResults, usePaperPerformance, useSeriesScores } from "@/hooks/usePolling";
import { WilsonChart } from "@/components/charts/WilsonChart";
import { SectionHeader } from "@/components/trading/StatRow";
import { cn, formatPct, formatCents } from "@/lib/utils";
import { api } from "@/lib/api";
import { toast } from "sonner";
import type { BacktestResult, Verdict } from "@/types/trading";

function VerdictBadge({ v }: { v: Verdict }) {
  return (
    <span className={cn(
      "inline-flex rounded px-1.5 py-0.5 text-2xs font-bold uppercase",
      v === "PASS"         ? "bg-green/10 text-green" :
      v === "FAIL"         ? "bg-red/10 text-red" :
                             "bg-muted text-muted-fg"
    )}>
      {v}
    </span>
  );
}

function WilsonCell({ lb }: { lb: number }) {
  return (
    <span className={cn("font-mono text-xs tabular",
      lb > 0.02 ? "text-green" : lb > 0 ? "text-orange" : "text-red"
    )}>
      {lb.toFixed(3)}
    </span>
  );
}

export default function ResearchPage() {
  const { data: btData, isLoading: btLoading } = useBacktestResults();
  const { data: paper } = usePaperPerformance();
  const { data: scores } = useSeriesScores();

  const results = btData?.results ?? [];
  const deduped: BacktestResult[] = [];
  const seen = new Set<string>();
  for (const r of results) {
    if (!seen.has(r.series)) { seen.add(r.series); deduped.push(r); }
  }
  deduped.sort((a, b) => b.wilson_lb - a.wilson_lb);

  async function runBacktest() {
    const p = toast.loading("Running backtest sweep…");
    try {
      await api.runBacktest();
      toast.success("Backtest running — refresh in 30s", { id: p });
    } catch {
      toast.error("Failed to start backtest", { id: p });
    }
  }

  return (
    <div className="max-w-3xl px-4 pb-10 pt-6">
      {/* Paper Performance */}
      {paper && paper.n > 0 && (
        <div className="mb-4 rounded-xl border border-border bg-surface p-4">
          <SectionHeader title="Paper Trade Performance" />
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: "Fills", value: paper.n },
              { label: "Win Rate", value: formatPct(paper.win_rate), valueClass: paper.win_rate > 0.55 ? "text-green" : "text-red" },
              { label: "Total P&L", value: formatCents(paper.total_pnl_c), valueClass: paper.total_pnl_c > 0 ? "text-green" : "text-red" },
              { label: "Avg/Fill", value: formatCents(paper.avg_pnl_c), valueClass: (paper.avg_pnl_c ?? 0) > 0 ? "text-green" : "text-red" },
            ].map(({ label, value, valueClass }) => (
              <div key={label} className="rounded-lg border border-border bg-surface2 p-3 text-center">
                <div className={cn("text-xl font-bold tabular", valueClass ?? "text-fg")}>{value}</div>
                <div className="mt-0.5 text-2xs uppercase tracking-widest text-muted-fg">{label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Wilson LB Chart */}
      {deduped.length > 0 && (
        <div className="mb-4 rounded-xl border border-border bg-surface p-4">
          <SectionHeader title="Wilson 95% Lower Bound by Series" />
          <p className="mb-3 text-xs text-muted-fg">
            Green = confirmed edge (LB &gt; 0 in both halves). Zero line = statistical break-even.
          </p>
          <WilsonChart results={deduped} />
        </div>
      )}

      {/* Backtest Table */}
      <div className="rounded-xl border border-border bg-surface">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-2xs font-semibold uppercase tracking-widest text-muted-fg">
            Backtest Results ({deduped.length} series)
          </h2>
          <button
            onClick={runBacktest}
            className="rounded-md bg-blue/10 px-3 py-1 text-xs font-semibold text-blue hover:bg-blue/20 transition-colors"
          >
            Run Sweep
          </button>
        </div>

        {btLoading ? (
          <p className="p-8 text-center text-sm text-muted-fg">Loading…</p>
        ) : deduped.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-fg">
            No results yet — run a sweep to see which series have edge
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  {["Series", "n", "Win Rate", "Avg EV", "Wilson LB", "LB H1", "LB H2", "Verdict"].map((h) => (
                    <th key={h} className="px-3 py-2.5 text-left font-semibold text-muted-fg">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {deduped.map((r) => (
                  <tr key={r.series} className="border-b border-border/50 hover:bg-surface2 transition-colors">
                    <td className="px-3 py-2.5 font-mono font-semibold text-fg">{r.series}</td>
                    <td className="px-3 py-2.5 tabular text-fg-3">{r.n_trades}</td>
                    <td className={cn("px-3 py-2.5 font-mono tabular", r.win_rate > 0.55 ? "text-green" : "text-fg-2")}>
                      {formatPct(r.win_rate)}
                    </td>
                    <td className={cn("px-3 py-2.5 font-mono tabular", r.avg_ev_c > 0 ? "text-green" : "text-red")}>
                      {r.avg_ev_c.toFixed(2)}¢
                    </td>
                    <td className="px-3 py-2.5"><WilsonCell lb={r.wilson_lb} /></td>
                    <td className="px-3 py-2.5"><WilsonCell lb={r.wilson_lb_h1} /></td>
                    <td className="px-3 py-2.5"><WilsonCell lb={r.wilson_lb_h2} /></td>
                    <td className="px-3 py-2.5"><VerdictBadge v={r.verdict} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
