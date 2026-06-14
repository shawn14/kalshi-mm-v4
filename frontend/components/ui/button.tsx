import { cn } from "@/lib/utils";
import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "danger" | "success" | "ghost" | "outline";

const variants: Record<Variant, string> = {
  primary: "bg-accent text-white hover:bg-accent-hover",
  danger:  "bg-danger-muted text-danger hover:bg-red-900",
  success: "bg-success-muted text-success hover:bg-green-900",
  ghost:   "bg-muted text-fg-secondary hover:bg-muted/80",
  outline: "border border-border text-fg-secondary hover:bg-muted",
};

export function Button({
  variant = "primary", className, children, ...props
}: { variant?: Variant } & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-md px-4 py-2.5 text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-mono",
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
