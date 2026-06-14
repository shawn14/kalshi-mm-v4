"use client";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { cn } from "@/lib/utils";

interface DataPoint { time: string; pnl: number }

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const v = payload[0].value as number;
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs font-mono">
      <span className={cn("font-bold", v >= 0 ? "text-success" : "text-danger")}>
        {v >= 0 ? "+" : ""}${v.toFixed(2)}
      </span>
      <span className="ml-2 text-muted-fg">{payload[0].payload.time}</span>
    </div>
  );
};

export function PnLChart({ data, height = 120 }: { data: DataPoint[]; height?: number }) {
  const isPositive = (data.at(-1)?.pnl ?? 0) >= 0;
  const color = isPositive ? "#22c55e" : "#ef4444";

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="time" hide />
        <YAxis hide domain={["auto", "auto"]} />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="#27272a" strokeDasharray="3 3" />
        <Area
          type="monotone"
          dataKey="pnl"
          stroke={color}
          strokeWidth={2}
          fill="url(#pnlGrad)"
          dot={false}
          activeDot={{ r: 3, fill: color }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
