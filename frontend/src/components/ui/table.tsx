import * as React from "react";

import { cn } from "@/lib/utils";

export type TableProps = React.TableHTMLAttributes<HTMLTableElement>;
export type TableSectionProps = React.HTMLAttributes<HTMLTableSectionElement>;
export type TableRowProps = React.HTMLAttributes<HTMLTableRowElement>;
export type TableCellProps = React.TdHTMLAttributes<HTMLTableCellElement> & {
  numeric?: boolean;
};
export type TableHeadProps = React.ThHTMLAttributes<HTMLTableCellElement>;
export type DataCardProps = React.HTMLAttributes<HTMLDivElement>;

export const Table = React.forwardRef<HTMLTableElement, TableProps>(
  ({ className, ...props }, ref) => (
    <div className="w-full overflow-auto">
      <table ref={ref} className={cn("w-full text-sm", className)} {...props} />
    </div>
  ),
);
Table.displayName = "Table";

export const TableHeader = React.forwardRef<HTMLTableSectionElement, TableSectionProps>(
  ({ className, ...props }, ref) => (
    <thead
      ref={ref}
      className={cn("[&_tr]:border-b [&_tr]:border-hairline", className)}
      {...props}
    />
  ),
);
TableHeader.displayName = "TableHeader";

export const TableBody = React.forwardRef<HTMLTableSectionElement, TableSectionProps>(
  ({ className, ...props }, ref) => (
    <tbody ref={ref} className={cn("[&_tr:last-child]:border-0", className)} {...props} />
  ),
);
TableBody.displayName = "TableBody";

export const TableRow = React.forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn("border-b border-hairline-soft transition-colors", className)}
      {...props}
    />
  ),
);
TableRow.displayName = "TableRow";

export const TableHead = React.forwardRef<HTMLTableCellElement, TableHeadProps>(
  ({ className, ...props }, ref) => (
    <th
      ref={ref}
      className={cn(
        "h-11 px-4 text-left align-middle text-caption font-medium uppercase tracking-[0.16em] text-muted",
        className,
      )}
      {...props}
    />
  ),
);
TableHead.displayName = "TableHead";

export const TableCell = React.forwardRef<HTMLTableCellElement, TableCellProps>(
  ({ className, numeric, ...props }, ref) => (
    <td
      ref={ref}
      className={cn(
        "px-4 py-3 align-middle text-body",
        numeric && "font-mono tabular-nums text-ink",
        className,
      )}
      {...props}
    />
  ),
);
TableCell.displayName = "TableCell";

export const DataCard = React.forwardRef<HTMLDivElement, DataCardProps>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("rounded-md border border-hairline bg-canvas p-4 shadow-card", className)}
      {...props}
    />
  ),
);
DataCard.displayName = "DataCard";
