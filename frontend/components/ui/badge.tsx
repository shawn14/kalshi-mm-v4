import { cn } from "@/lib/utils";

type Variant = "pass" | "fail" | "insufficient" | "live" | "paper" | "yes" | "no" | "default";

const variants: Record<Variant, string> = {
  pass:         "bg-success-muted text-success",
  fail:         "bg-danger-muted text-danger",
  insufficient: "bg-muted text-muted-fg",
  live:         "bg-accent-muted text-accent",
  paper:        "bg-warning-muted text-warning",
  yes:          "bg-success-muted text-success",
  no:           "bg-danger-muted text-danger",
  default:      "bg-muted text-fg",
};

export function Badge({ variant = "default", children, className }: {
  variant?: Variant;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide", variants[variant], className)}>
      {children}
    </span>
  );
}
