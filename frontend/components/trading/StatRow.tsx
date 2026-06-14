import { cn } from "@/lib/utils";

export function StatRow({ label, value, valueClass, border = true }: {
  label: string;
  value: React.ReactNode;
  valueClass?: string;
  border?: boolean;
}) {
  return (
    <div className={cn(
      "flex items-center justify-between py-2.5",
      border && "border-b separator"
    )}>
      <span className="text-sm text-fg-3">{label}</span>
      <span className={cn("text-sm font-semibold tabular", valueClass)}>{value}</span>
    </div>
  );
}

export function SectionHeader({ title, action }: { title: string; action?: React.ReactNode }) {
  return (
    <div className="mb-2 flex items-center justify-between">
      <h2 className="text-2xs font-semibold uppercase tracking-widest text-muted-fg">{title}</h2>
      {action}
    </div>
  );
}
