import type { Cell } from "./types";

export const RATIO_COLUMN = /(rate|share|ratio|pct|percent)/i;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

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

/**
 * "2018-03-01" -> "Mar 2018", "2018-03-15" -> "Mar 15, 2018".
 * Parsed by hand: new Date("2018-03-01") is UTC midnight, which shows as Feb 28 in US time zones.
 */
export function formatDateTick(value: string): string {
  const [year, month, day] = value.slice(0, 10).split("-");
  const name = MONTHS[Number(month) - 1];
  if (!name) return value;
  return !day || day === "01" ? `${name} ${year}` : `${name} ${Number(day)}, ${year}`;
}