"use client";
import { useMMQuotes, useMMInventory } from "@/hooks/usePolling";
import { SectionHeader } from "@/components/trading/StatRow";
import { cn } from "@/lib/utils";

function PriceZone({ mid }: { mid: number }) {
  if (mid >= 40 && mid <= 60) return <span className="text-green text-2xs font-bold">CORE</span>;
  if ((mid >= 30 && mid < 40) || (mid > 60 && mid <= 70)) return <span className="text-orange text-2xs font-bold">EDGE</span>;
  return <span className="text-red text-2xs font-bold">DEF</span>;
}

function MidBar({ mid }: { mid: number }) {
  const pct = mid; // 0-100c maps to 0-100%
  const color = mid >= 40 && mid <= 60 ? "bg-green" :
                (mid >= 30 && mid <= 70) ? "bg-orange" : "bg-red";
  return (
    <div className="relative h-2 w-full rounded-full bg-surface2">
      {/* Core zone shading */}
      <div className="absolute inset-y-0 left-[40%] right-[40%] rounded-full bg-green/10" />
      {/* Mid marker */}
      <div className={cn("absolute top-0 h-2 w-1 rounded-sm", color)}
           style={{ left: `calc(${pct}% - 2px)` }} />
    </div>
  );
}

export default function MarketsPage() {
  const { data: quotesData } = useMMQuotes();
  const { data: invData } = useMMInventory();

  const orders = quotesData?.orders ?? [];
  const inventory = invData?.inventory ?? [];

  // Group orders by ticker
  const byTicker = new Map<string, { yes?: number; no?: number; count: number }>();
  for (const o of orders) {
    const cur = byTicker.get(o.ticker) ?? { count: 0 };
    if (o.side === "yes") cur.yes = o.price_c;
    else cur.no = o.price_c;
    cur.count++;
    byTicker.set(o.ticker, cur);
  }

  const invByTicker = new Map(inventory.map((i) => [i.ticker, i]));
  const tickers = Array.from(byTicker.keys());

  return (
    <div className="max-w-3xl px-4 pb-10 pt-6">
      {/* Legend */}
      <div className="mb-4 flex flex-wrap gap-3 text-2xs text-muted-fg">
        <span className="flex items-center gap-1"><span className="inline-block h-2 w-4 rounded-sm bg-green/10 border border-green/30" /> 40-60c core zone</span>
        <span className="flex items-center gap-1"><span className="inline-block h-2 w-4 rounded-sm bg-orange/10 border border-orange/30" /> 30-40 / 60-70 edge</span>
        <span className="flex items-center gap-1"><span className="inline-block h-2 w-4 rounded-sm bg-red/10 border border-red/30" /> 20-30 / 70-80 defensive</span>
      </div>

      <div className="rounded-xl border border-border bg-surface">
        <div className="border-b border-border px-4 py-3">
          <h2 className="text-2xs font-semibold uppercase tracking-widest text-muted-fg">
            Active Markets ({tickers.length})
          </h2>
        </div>

        {tickers.length === 0 ? (
          <p className="p-8 text-center text-sm text-muted-fg">
            No active quotes — engine may not be running
          </p>
        ) : (
          <div className="divide-y divide-border/50">
            {tickers.map((ticker) => {
              const q = byTicker.get(ticker)!;
              const inv = invByTicker.get(ticker);
              const mid = q.yes != null && q.no != null
                ? ((q.yes + (100 - q.no)) / 2)
                : q.yes ?? (100 - (q.no ?? 50));
              const spread = q.yes != null && q.no != null ? (100 - q.no) - q.yes : null;

              return (
                <div key={ticker} className="px-4 py-3 hover:bg-surface2 transition-colors">
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <span className="min-w-0 flex-1 truncate font-mono text-sm text-fg-2">{ticker}</span>
                    <div className="flex shrink-0 items-center gap-2">
                      <PriceZone mid={mid} />
                      {spread != null && (
                        <span className={cn(
                          "font-mono text-xs font-semibold tabular",
                          spread >= 7 ? "text-green" : "text-orange"
                        )}>
                          {spread.toFixed(0)}¢ sp
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Mid bar */}
                  <MidBar mid={mid} />

                  {/* Bid/ask + inventory */}
                  <div className="mt-2 flex items-center justify-between text-xs">
                    <div className="flex gap-3">
                      {q.yes != null && (
                        <span className="text-green font-mono tabular">B {q.yes}¢</span>
                      )}
                      {q.no != null && (
                        <span className="text-red font-mono tabular">A {100 - q.no}¢</span>
                      )}
                    </div>
                    {inv && (
                      <span className={cn(
                        "font-mono tabular font-semibold",
                        inv.net_yes > 0 ? "text-green" : inv.net_yes < 0 ? "text-red" : "text-muted-fg"
                      )}>
                        {inv.net_yes > 0 ? "+" : ""}{inv.net_yes} net
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
