"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity, BarChart2, BookOpen, Shield, Settings, Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSystemStatus } from "@/hooks/usePolling";

const NAV = [
  { href: "/",          label: "Live",      icon: Activity },
  { href: "/markets",   label: "Markets",   icon: BarChart2 },
  { href: "/research",  label: "Research",  icon: BookOpen },
  { href: "/risk",      label: "Risk",      icon: Shield },
  { href: "/control",   label: "Control",   icon: Settings },
];

export function Sidebar() {
  const path = usePathname();
  const { data: sys } = useSystemStatus();

  const isLive = sys && !sys.paper_mode && sys.engine_running;
  const isPaper = sys?.paper_mode;
  const isKilled = sys?.kill_switch;
  const isCB = sys?.circuit_breaker;

  return (
    <aside className="fixed left-0 top-0 z-50 flex h-dvh w-16 flex-col items-center border-r border-border bg-surface py-4 md:w-56 md:items-start md:px-3">
      {/* Logo */}
      <div className="mb-6 flex items-center gap-2 px-1">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue/20">
          <Zap className="h-4 w-4 text-blue" />
        </div>
        <span className="hidden text-sm font-bold tracking-tight text-fg md:block">
          Kalshi MM
          <span className="ml-1 text-2xs font-normal text-muted-fg">v4</span>
        </span>
      </div>

      {/* Status pill */}
      <div className="mb-4 hidden w-full md:block">
        <div className={cn(
          "flex items-center gap-2 rounded-md px-2.5 py-1.5 text-xs font-semibold",
          isKilled || isCB ? "bg-red/10 text-red" :
          isLive          ? "bg-green/10 text-green" :
          isPaper         ? "bg-orange/10 text-orange" :
                            "bg-muted text-muted-fg"
        )}>
          <span className={cn("h-1.5 w-1.5 rounded-full",
            isKilled || isCB ? "bg-red animate-pulse" :
            isLive           ? "bg-green animate-pulse" :
            isPaper          ? "bg-orange" : "bg-muted-fg"
          )} />
          {isKilled ? "KILLED" : isCB ? "BREAKER" : isLive ? "LIVE" : isPaper ? "PAPER" : "STOPPED"}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex w-full flex-1 flex-col gap-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-2 py-2.5 text-sm font-medium transition-colors",
                "md:px-2.5",
                active
                  ? "bg-blue/10 text-blue"
                  : "text-fg-3 hover:bg-surface2 hover:text-fg-2"
              )}
            >
              <Icon className="h-[18px] w-[18px] shrink-0" />
              <span className="hidden md:block">{label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
