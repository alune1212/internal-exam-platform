import { useMemo, type ReactNode } from "react";
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
  rowKey?: (row: TData) => string | number;
  rowClassName?: (row: TData) => string | undefined;
  mobileRowClassName?: (row: TData) => string | undefined;
  renderMobileRow?: (row: Row<TData>) => ReactNode;
};

function defaultMobileCardClassName(): string {
  return "rounded-md border border-hairline bg-canvas p-4 shadow-card";
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
              "flex items-baseline justify-between gap-3 py-1 text-body",
              priority === "primary" && "font-display text-lg font-semibold",
            )}
          >
            <span className="text-caption uppercase tracking-[0.16em] text-muted">{label}</span>
            <span className="text-right">{value}</span>
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
  rowKey,
  rowClassName,
  mobileRowClassName,
  renderMobileRow,
}: SimpleDataTableProps<TData>) {
  const isDesktop = useMediaQuery(MD.md);
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getRowId: (row, index) =>
      rowKey ? String(rowKey(row)) : String((row as { id?: number | string }).id ?? index),
  });

  const tableRows = table.getRowModel().rows;
  const isEmpty = tableRows.length === 0;
  const renderRow = renderMobileRow ?? defaultMobileRow;
  const mobileNodes = useMemo(
    () =>
      isEmpty
        ? []
        : tableRows.map((row) => (
            <div
              key={row.id}
              data-testid="mobile-row-card"
              className={cn(defaultMobileCardClassName(), mobileRowClassName?.(row.original))}
            >
              {renderRow(row)}
            </div>
          )),
    [isEmpty, mobileRowClassName, renderRow, tableRows],
  );

  if (isEmpty) {
    if (isDesktop) {
      return (
        <Table>
          <TableBody>
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center text-muted">
                {emptyText}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      );
    }

    return (
      <div className="rounded-md border border-hairline bg-canvas p-6 text-center text-muted">
        {emptyText}
      </div>
    );
  }

  if (!isDesktop) {
    return <div className="flex flex-col gap-3">{mobileNodes}</div>;
  }

  return (
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
  );
}
