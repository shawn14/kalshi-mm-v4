"use client";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine,
} from "recharts";

interface SpreadBucket { range: string; count: number; ev: number }

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload as SpreadBucket;
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs font-mono">
      <div className="text-fg font-bold">{d.range}</div>
      <div className="text-muted-fg">{d.count} markets</div>
      <div className={d.ev >= 0 ? "text-success" : "text-danger"}>
        EV: {d.ev >= 0 ? "+" : ""}{d.ev.toFixed(2)}¢
      </div>
    </div>
  );
};

export function SpreadDistChart({ data, height = 140 }: { data: SpreadBucket[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
        <XAxis dataKey="range" tick={{ fontSize: 9, fill: "#71717a" }} />
        <YAxis tick={{ fontSize: 9, fill: "#71717a" }} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.ev > 0 ? "#22c55e" : "#ef4444"} fillOpacity={0.7} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
