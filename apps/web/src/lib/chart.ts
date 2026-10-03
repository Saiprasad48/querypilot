import { RATIO_COLUMN } from "./format";
import type { Cell, ChartSpec, ResultTable } from "./types";

const DATE_LIKE = /^\d{4}-\d{2}(-\d{2})?/;
export const MAX_SERIES = 4;
export const MAX_POINTS = 60;

export type ChartPlan =
  | { kind: "number"; column: string; value: number }
  | {
      kind: "bar" | "line";
      x: string;
      y: string[];
      data: Record<string, Cell>[];
      horizontal: boolean;
      isDate: boolean;
    };

const isNumber = (v: Cell): v is number => typeof v === "number" && Number.isFinite(v);

/**
 * Turn the model's chart suggestion into a safe, renderable plan, or null for "table only".
 * The model suggests; this code decides. It never trusts column names or chart types blindly.
 */
export function planChart(spec: ChartSpec, table: ResultTable): ChartPlan | null {
  const { columns, rows } = table;
  if (rows.length === 0 || spec.type === "table") return null;

  const col = (name: string) => columns.indexOf(name);
  const numeric = columns.filter(
    (c) => rows.some((r) => isNumber(r[col(c)])) && rows.every((r) => r[col(c)] === null || isNumber(r[col(c)])),
  );

  // A single row is a headline number, not a chart.
  if (spec.type === "number" || rows.length === 1) {
    const column = spec.y.find((c) => numeric.includes(c)) ?? numeric[0];
    const value = column ? rows[0][col(column)] : null;
    return column && isNumber(value) ? { kind: "number", column, value } : null;
  }

  const x = spec.x && columns.includes(spec.x) ? spec.x : columns.find((c) => !numeric.includes(c));
  if (!x) return null;

  let y = spec.y.filter((c) => numeric.includes(c) && c !== x);
  if (y.length === 0) y = numeric.filter((c) => c !== x).slice(0, 1);
  if (y.length === 0) return null;

  // One axis only: keep the series that share the first series' unit (ratio vs. count/money).
  const firstIsRatio = RATIO_COLUMN.test(y[0]);
  y = y.filter((c) => RATIO_COLUMN.test(c) === firstIsRatio).slice(0, MAX_SERIES);

  const isDate = rows.every((r) => typeof r[col(x)] === "string" && DATE_LIKE.test(r[col(x)] as string));
  const kind = spec.type === "line" || (isDate && spec.type !== "bar") ? "line" : "bar";
  const textCategories = typeof rows[0][col(x)] === "string" && !isDate;
  const data = rows
    .slice(0, MAX_POINTS)
    .map((r) => Object.fromEntries(columns.map((c, i) => [c, r[i]])));

  return { kind, x, y, data, horizontal: kind === "bar" && textCategories, isDate };
}