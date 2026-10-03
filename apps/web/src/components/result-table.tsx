import { formatCell, humanize } from "@/lib/format";
import type { ResultTable } from "@/lib/types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const MAX_VISIBLE_ROWS = 50;

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
      <p className="text-xs text-muted-foreground">
        {table.row_count.toLocaleString()} row{table.row_count === 1 ? "" : "s"}
        {table.row_count > MAX_VISIBLE_ROWS && `, showing the first ${MAX_VISIBLE_ROWS}`}
      </p>
    </div>
  );
}