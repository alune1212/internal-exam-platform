import { render, screen, within } from "@testing-library/react";
import type { ColumnDef } from "@tanstack/react-table";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SimpleDataTable } from "../SimpleDataTable";

type Row = { id: number; name: string; score: number };

const columns: ColumnDef<Row>[] = [
  {
    accessorKey: "id",
    header: "ID",
    meta: { mobilePriority: false },
  },
  {
    accessorKey: "name",
    header: "NAME",
  },
  {
    accessorKey: "score",
    header: "SCORE",
    meta: { mobilePriority: "primary" },
  },
];

const wideColumns: ColumnDef<Row>[] = Array.from({ length: 8 }, (_, index) => ({
  id: `column-${index}`,
  header: `COLUMN-${index + 1}`,
  cell: ({ row }) => `${row.original.name}-${index + 1}`,
}));

const rows: Row[] = [
  { id: 1, name: "Ada", score: 98 },
  { id: 2, name: "Linus", score: 72 },
];

const setMatchMedia = (matches: boolean) => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      get matches() {
        return query.includes("1024") ? matches : true;
      },
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }),
  });
};

describe("SimpleDataTable", () => {
  beforeEach(() => setMatchMedia(true));
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a desktop table with thead and tbody", () => {
    render(<SimpleDataTable columns={columns} data={rows} />);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("NAME")).toBeInTheDocument();
    expect(screen.getByText("Ada")).toBeInTheDocument();
    expect(screen.getByRole("table").parentElement?.parentElement).toHaveAttribute(
      "data-responsive-data",
      "",
    );
  });

  it("renders wide tables as cards even on desktop", () => {
    render(<SimpleDataTable columns={wideColumns} data={rows} />);

    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getAllByTestId("mobile-row-card")).toHaveLength(2);
  });

  it("renders the empty state when data is empty", () => {
    render(<SimpleDataTable columns={columns} data={[]} />);

    expect(screen.getByText("暂无数据")).toBeInTheDocument();
  });

  it("renders a card list on mobile and hides low-priority columns", () => {
    setMatchMedia(false);
    render(<SimpleDataTable columns={columns} data={rows} />);

    expect(screen.queryByRole("table")).toBeNull();

    const cards = screen.getAllByTestId("mobile-row-card");
    expect(cards).toHaveLength(2);
    expect(cards[0]).toHaveClass("rounded-md");

    const adaCard = cards[0]!;
    expect(within(adaCard).queryByText("1")).toBeNull();
    expect(within(adaCard).getByText("98")).toBeInTheDocument();
    expect(within(adaCard).getByText("Ada")).toBeInTheDocument();
    expect(adaCard.parentElement).toHaveAttribute("data-table-mode", "cards");
  });

  it("lets mobile primary values inherit dark card text colour", () => {
    setMatchMedia(false);
    render(
      <SimpleDataTable
        columns={columns}
        data={rows}
        mobileRowClassName={(row) => (row.id === 1 ? "bg-ink text-white" : undefined)}
      />,
    );

    const adaCard = screen.getAllByTestId("mobile-row-card")[0]!;
    expect(adaCard).toHaveClass("text-white");
    expect(within(adaCard).getByText("98").parentElement).not.toHaveClass("text-ink");
  });

  it("respects a custom emptyText", () => {
    render(<SimpleDataTable columns={columns} data={[]} emptyText="空空如也" />);

    expect(screen.getByText("空空如也")).toBeInTheDocument();
  });

  it("inherits the enclosing table surface for a mobile empty state", () => {
    setMatchMedia(false);
    render(<SimpleDataTable columns={columns} data={[]} />);

    expect(screen.getByText("暂无数据")).toHaveAttribute("data-table-empty");
    expect(screen.getByText("暂无数据")).not.toHaveClass("border", "bg-canvas", "rounded-md");
  });

  it("keeps long unbroken values inside the responsive card representation", () => {
    setMatchMedia(false);
    render(
      <SimpleDataTable
        columns={columns}
        data={[{ id: 1, name: "candidate-with-a-very-long-unbroken-identifier", score: 98 }]}
      />,
    );

    const card = screen.getByTestId("mobile-row-card");
    expect(card).toHaveTextContent("candidate-with-a-very-long-unbroken-identifier");
    expect(card.querySelector("span.flex-1")).toHaveClass("break-words");
  });

  it("refreshes mobile cells when interaction state changes without replacing row data", () => {
    setMatchMedia(false);
    const stateColumns = (pending: boolean): ColumnDef<Row>[] => [
      {
        id: "state",
        header: "状态",
        cell: () => (pending ? "处理中" : "可操作"),
        meta: { mobilePriority: "primary", mobileLabel: "状态" },
      },
    ];
    const stableRows = [rows[0]!];
    const { rerender } = render(
      <SimpleDataTable columns={stateColumns(false)} data={stableRows} />,
    );

    expect(screen.getByText("可操作")).toBeInTheDocument();
    rerender(<SimpleDataTable columns={stateColumns(true)} data={stableRows} />);

    expect(screen.getByText("处理中")).toBeInTheDocument();
    expect(screen.queryByText("可操作")).not.toBeInTheDocument();
  });
});
