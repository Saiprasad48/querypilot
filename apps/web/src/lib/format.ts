import type { Cell } from "./types";

const RATIO_COLUMN = /(rate|share|ratio|pct|percent)/i;

/** Format a result cell for display: ratios as %, big numbers with separators. */
export function formatCell(column: string, value: Cell): string {
  if (value === null) return "∅";
  if (typeof value === "number") {
    if (RATIO_COLUMN.test(column) && value >= 0 && value <= 1) {
      return `${(value * 100).toFixed(2)}%`;
    }
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

/** "late_delivery_rate" -> "Late delivery rate" */
export function humanize(name: string): string {
  const text = name.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}