import { describe, expect, it } from "vitest";

import { planChart } from "./chart";
import type { ChartSpec, ResultTable } from "./types";

const spec = (over: Partial<ChartSpec>): ChartSpec => ({
  type: "bar",
  x: null,
  y: [],
  title: "",
  ...over,
});

describe("planChart", () => {
  it("draws a line for monthly trends", () => {
    const table: ResultTable = {
      columns: ["month", "revenue"],
      rows: [["2018-01-01", 950000], ["2018-02-01", 880000], ["2018-03-01", 1020000]],
      row_count: 3,
    };
    const plan = planChart(spec({ type: "line", x: "month", y: ["revenue"] }), table);
    expect(plan).toMatchObject({ kind: "line", isDate: true, horizontal: false });
  });

  it("uses horizontal bars for text categories", () => {
    const table: ResultTable = {
      columns: ["category", "items_sold"],
      rows: [["health_beauty", 5841], ["bed_bath_table", 5810]],
      row_count: 2,
    };
    const plan = planChart(spec({ x: "category", y: ["items_sold"] }), table);
    expect(plan).toMatchObject({ kind: "bar", horizontal: true, y: ["items_sold"] });
  });

  it("never mixes units on one axis", () => {
    const table: ResultTable = {
      columns: ["state", "delivered_orders", "late_delivery_rate"],
      rows: [["AL", 198, 0.2071], ["RR", 18, 0.1667]],
      row_count: 2,
    };
    const plan = planChart(spec({ x: "state", y: ["delivered_orders", "late_delivery_rate"] }), table);
    expect(plan && plan.kind !== "number" && plan.y).toEqual(["delivered_orders"]);
  });

  it("turns a single row into a headline number", () => {
    const table: ResultTable = { columns: ["delivered_orders"], rows: [[43428]], row_count: 1 };
    expect(planChart(spec({ y: ["delivered_orders"] }), table)).toEqual({
      kind: "number",
      column: "delivered_orders",
      value: 43428,
    });
  });

  it("ignores columns the model invented", () => {
    const table: ResultTable = {
      columns: ["state", "orders"],
      rows: [["SP", 40000], ["RJ", 12000]],
      row_count: 2,
    };
    const plan = planChart(spec({ x: "region", y: ["revenue"] }), table);
    expect(plan).toMatchObject({ kind: "bar", x: "state", y: ["orders"] });
  });

  it("returns null when the model asks for a table", () => {
    const table: ResultTable = { columns: ["a", "b"], rows: [["x", 1], ["y", 2]], row_count: 2 };
    expect(planChart(spec({ type: "table" }), table)).toBeNull();
  });
});