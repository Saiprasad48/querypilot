"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { planChart } from "@/lib/chart";
import { formatCell, formatDateTick, humanize } from "@/lib/format";
import type { ChartSpec, ResultTable } from "@/lib/types";

const seriesColor = (i: number) => `var(--series-${i + 1})`;

const axis = {
  stroke: "var(--muted-foreground)",
  fontSize: 12,
  tickLine: false,
  axisLine: false,
} as const;

const tooltipStyle = {
  background: "var(--popover)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--popover-foreground)",
  fontSize: 12,
};

export function AnswerChart({ spec, table }: { spec: ChartSpec; table: ResultTable }) {
  const plan = planChart(spec, table);
  if (!plan) return null;

  if (plan.kind === "number") {
    return (
      <div className="py-8 text-center">
        <div className="text-5xl font-semibold tabular-nums">
          {formatCell(plan.column, plan.value)}
        </div>
        <div className="mt-2 text-sm text-muted-foreground">{humanize(plan.column)}</div>
      </div>
    );
  }

  const formatX = (v: unknown) =>
    plan.isDate ? formatDateTick(String(v)) : String(v).replace(/_/g, " ");
  const formatY = (v: unknown) => formatCell(plan.y[0], v as number);
  const tooltipFormatter = (value: unknown, name: unknown) => [
    formatCell(String(name), value as number),
    humanize(String(name)),
  ];
  const legend =
    plan.y.length > 1 ? <Legend formatter={(v) => humanize(String(v))} /> : null;

  if (plan.kind === "line") {
    return (
      <div className="space-y-2">
        {spec.title && <h3 className="text-sm font-medium">{spec.title}</h3>}
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={plan.data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis dataKey={plan.x} tickFormatter={formatX} minTickGap={24} {...axis} />
            <YAxis tickFormatter={formatY} width={72} domain={["auto", "auto"]} {...axis} />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={formatX}
              formatter={tooltipFormatter}
            />
            {legend}
            {plan.y.map((c, i) => (
              <Line
                key={c}
                dataKey={c}
                type="monotone"
                stroke={seriesColor(i)}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  const height = plan.horizontal ? Math.max(160, plan.data.length * 36 + 40) : 280;
  return (
    <div className="space-y-2">
      {spec.title && <h3 className="text-sm font-medium">{spec.title}</h3>}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={plan.data}
          layout={plan.horizontal ? "vertical" : "horizontal"}
          margin={{ top: 8, right: 24, bottom: 0, left: 0 }}
        >
          <CartesianGrid
            horizontal={!plan.horizontal}
            vertical={plan.horizontal}
            stroke="var(--border)"
          />
          {plan.horizontal ? (
            <>
              <XAxis type="number" tickFormatter={formatY} {...axis} />
              <YAxis
                type="category"
                dataKey={plan.x}
                tickFormatter={formatX}
                width={150}
                {...axis}
              />
            </>
          ) : (
            <>
              <XAxis dataKey={plan.x} tickFormatter={formatX} minTickGap={16} {...axis} />
              <YAxis tickFormatter={formatY} width={72} {...axis} />
            </>
          )}
          <Tooltip
            cursor={{ fill: "var(--muted)", opacity: 0.6 }}
            contentStyle={tooltipStyle}
            labelFormatter={formatX}
            formatter={tooltipFormatter}
          />
          {legend}
          {plan.y.map((c, i) => (
            <Bar
              key={c}
              dataKey={c}
              fill={seriesColor(i)}
              maxBarSize={24}
              radius={plan.horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}