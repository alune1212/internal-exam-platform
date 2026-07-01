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

const rows: Row[] = [
  { id: 1, name: "Ada", score: 98 },
  { id: 2, name: "Linus", score: 72 },
];

const setMatchMedia = (matches: boolean) => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      get matches() {
        return query.includes("768") ? matches : true;
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
});
