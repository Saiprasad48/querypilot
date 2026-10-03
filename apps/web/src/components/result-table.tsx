"use client";

import { Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCell, humanize } from "@/lib/format";
import type { Cell, ResultTable } from "@/lib/types";

const MAX_VISIBLE_ROWS = 50;

function toCsv(table: ResultTable): string {
  const escape = (v: Cell) => {
    const s = v === null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [table.columns, ...table.rows].map((row) => row.map(escape).join(",")).join("\n");
}

function downloadCsv(table: ResultTable) {
  const url = URL.createObjectURL(new Blob([toCsv(table)], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "querypilot-result.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export function ResultTableView({ table }: { table: ResultTable }) {
  const rows = table.rows.slice(0, MAX_VISIBLE_ROWS);
  return (
    <div className="space-y-2">
      <div className="max-h-96 overflow-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {table.columns.map((c) => (
                <TableHead key={c}>{humanize(c)}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row, i) => (
              <TableRow key={i}>
                {row.map((value, j) => (
                  <TableCell
                    key={j}
                    className={typeof value === "number" ? "text-right tabular-nums" : ""}
                  >
                    {formatCell(table.columns[j], value)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          {table.row_count.toLocaleString()} row{table.row_count === 1 ? "" : "s"}
          {table.row_count > MAX_VISIBLE_ROWS && `, showing the first ${MAX_VISIBLE_ROWS}`}
        </p>
        <Button variant="ghost" size="sm" onClick={() => downloadCsv(table)}>
          <Download className="mr-1 h-4 w-4" />
          CSV
        </Button>
      </div>
    </div>
  );
}