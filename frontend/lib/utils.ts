import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCents(c: number | undefined | null, decimals = 2): string {
  if (c == null) return "—";
  return `${c >= 0 ? "+" : ""}${c.toFixed(decimals)}¢`;
}

export function formatUSD(v: number | undefined | null): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}$${Math.abs(v).toFixed(2)}`;
}

export function formatPct(v: number | undefined | null): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

export function shortTicker(ticker: string, max = 32): string {
  return ticker.length > max ? ticker.slice(0, max) + "…" : ticker;
}

export function wilsonColor(lb: number): string {
  if (lb > 0.02) return "text-success";
  if (lb > 0) return "text-warning";
  return "text-danger";
}
