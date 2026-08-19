import type { ReactNode } from "react";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type Row,
  type RowData,
} from "@tanstack/react-table";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { MD, useMediaQuery } from "@/lib/use-media-query";
import { cn } from "@/lib/utils";

// Hoisted so every render of `<SimpleDataTable>` receives the same row-model
// factory reference; TanStack downstream selectors can then memoize against
// the table options without re-running for an identity-only change.
const coreRowModel = getCoreRowModel();

type MobilePriority = "primary" | "secondary" | false;

declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData extends RowData, TValue> {
    mobilePriority?: MobilePriority;
    mobileLabel?: string;
  }
}

type SimpleDataTableProps<TData> = {
  columns: ColumnDef<TData>[];
  data: TData[];
  emptyText?: string;
  className?: string;
  rowKey?: (row: TData) => string | number;
  rowClassName?: (row: TData) => string | undefined;
  mobileRowClassName?: (row: TData) => string | undefined;
  renderMobileRow?: (row: Row<TData>) => ReactNode;
};

// Dense tables remain readable up to seven columns; wider datasets use the
// card renderer even on desktop so an admin rail cannot force page overflow.
const TABLE_COLUMN_LIMIT = 7;

function defaultMobileCardClassName(): string {
  return "min-w-0 rounded-md border border-hairline-soft bg-surface-card p-4";
}

function defaultMobileRow<TData>(row: Row<TData>): ReactNode {
  const visibleCells = row.getVisibleCells().filter((cell) => {
    const priority = cell.column.columnDef.meta?.mobilePriority;
    return priority !== false;
  });

  return (
    <>
      {visibleCells.map((cell) => {
        const label = cell.column.columnDef.meta?.mobileLabel ?? cell.column.id;
        const priority = cell.column.columnDef.meta?.mobilePriority;
        const value = flexRender(cell.column.columnDef.cell, cell.getContext());

        return (
          <div
            key={cell.id}
            className={cn(
              "flex min-w-0 items-baseline justify-between gap-3 py-1 text-body",
              priority === "primary" && "font-display text-display-sm font-semibold",
            )}
          >
            <span className="min-w-0 shrink-0 basis-2/5 break-words text-caption text-muted">
              {label}
            </span>
            <span className="min-w-0 flex-1 break-words text-right">{value}</span>
          </div>
        );
      })}
    </>
  );
}

export function SimpleDataTable<TData>({
  columns,
  data,
  emptyText = "暂无数据",
  className,
  rowKey,
  rowClassName,
  mobileRowClassName,
  renderMobileRow,
}: SimpleDataTableProps<TData>) {
  // Keep the dense table for wide workbench layouts only. At tablet widths the
  // surrounding admin rail and page gutters leave too little room for the
  // action-heavy columns, so the same records use the compact card renderer.
  const isDesktop = useMediaQuery(MD.lg);
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: coreRowModel,
    getRowId: (row, index) =>
      rowKey ? String(rowKey(row)) : String((row as { id?: number | string }).id ?? index),
  });

  const isWideTable = table.getAllLeafColumns().length > TABLE_COLUMN_LIMIT;
  const shouldRenderTable = isDesktop && !isWideTable;
  const tableRows = table.getRowModel().rows;
  const isEmpty = tableRows.length === 0;
  const renderRow = renderMobileRow ?? defaultMobileRow;
  const mobileNodes = isEmpty
    ? []
    : tableRows.map((row) => (
        <div
          key={row.id}
          data-testid="mobile-row-card"
          className={cn(defaultMobileCardClassName(), mobileRowClassName?.(row.original))}
        >
          {renderRow(row)}
        </div>
      ));

  if (isEmpty) {
    if (shouldRenderTable) {
      return (
        <div data-responsive-data="" data-table-mode="table" className={cn("min-w-0", className)}>
          <Table>
            <TableBody>
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-muted">
                  {emptyText}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      );
    }

    return (
      <div
        data-responsive-data=""
        data-table-mode="cards"
        data-table-empty
        className={cn("min-w-0 p-6 text-center text-muted", className)}
      >
        {emptyText}
      </div>
    );
  }

  if (!shouldRenderTable) {
    return (
      <div
        data-responsive-data=""
        data-table-mode="cards"
        className={cn("flex min-w-0 flex-col gap-3", className)}
      >
        {mobileNodes}
      </div>
    );
  }

  return (
    <div data-responsive-data="" data-table-mode="table" className={cn("min-w-0", className)}>
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {tableRows.map((row) => (
            <TableRow key={row.id} className={rowClassName?.(row.original)}>
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
