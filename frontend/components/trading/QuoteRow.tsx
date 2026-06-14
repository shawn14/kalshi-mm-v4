import { cn } from "@/lib/utils";
import type { ActiveOrder } from "@/types/trading";

export function QuoteRow({ order }: { order: ActiveOrder }) {
  const isYes = order.side === "yes";
  return (
    <div className="flex items-center gap-3 py-2.5 border-b separator last:border-0">
      {/* Side pill */}
      <span className={cn(
        "shrink-0 rounded px-1.5 py-0.5 text-2xs font-bold uppercase",
        isYes ? "bg-green/10 text-green" : "bg-red/10 text-red"
      )}>
        {order.side}
      </span>

      {/* Ticker */}
      <span className="min-w-0 flex-1 truncate text-xs text-fg-2 font-mono">
        {order.ticker}
      </span>

      {/* Price */}
      <span className="shrink-0 font-mono text-sm font-semibold text-fg tabular">
        {order.price_c}¢
      </span>

      {/* Count */}
      <span className="shrink-0 text-xs text-muted-fg">×{order.count}</span>
    </div>
  );
}
