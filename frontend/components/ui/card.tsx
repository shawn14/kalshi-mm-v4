import { cn } from "@/lib/utils";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("rounded-lg border border-border bg-surface p-4", className)}>
      {children}
    </div>
  );
}

export function CardTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-fg">
      {children}
    </p>
  );
}

export function StatCard({
  label, value, sub, valueClass,
}: { label: string; value: string | number; sub?: string; valueClass?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-surface p-4 text-center">
      <span className={cn("text-2xl font-bold tabular-nums", valueClass ?? "text-fg")}>{value}</span>
      <span className="mt-1 text-[10px] uppercase tracking-widest text-muted-fg">{label}</span>
      {sub && <span className="mt-0.5 text-xs text-muted-fg">{sub}</span>}
    </div>
  );
}
