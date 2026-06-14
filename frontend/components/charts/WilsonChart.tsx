"use client";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine,
} from "recharts";
import type { BacktestResult } from "@/types/trading";

interface Props { results: BacktestResult[] }

export function WilsonChart({ results }: Props) {
  const data = results
    .filter((r) => r.verdict !== "INSUFFICIENT")
    .sort((a, b) => b.wilson_lb - a.wilson_lb)
    .slice(0, 20)
    .map((r) => ({ series: r.series.replace("KX", ""), lb: r.wilson_lb, verdict: r.verdict }));

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 60, bottom: 0 }}>
        <XAxis type="number" domain={[-0.2, 0.3]} tick={{ fontSize: 9, fill: "#71717a" }} tickFormatter={(v) => v.toFixed(2)} />
        <YAxis type="category" dataKey="series" tick={{ fontSize: 9, fill: "#a1a1aa" }} width={60} />
        <Tooltip
          formatter={(v: number) => [`${v.toFixed(3)}`, "Wilson LB"]}
          contentStyle={{ background: "#111113", border: "1px solid #1c1c1f", fontSize: 11 }}
        />
        <ReferenceLine x={0} stroke="#27272a" strokeWidth={1} />
        <Bar dataKey="lb" radius={[0, 3, 3, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.lb > 0 ? "#22c55e" : "#ef4444"} fillOpacity={0.8} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
