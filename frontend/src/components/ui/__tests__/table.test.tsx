import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DataCard, TableBody, TableCell, TableHead, TableRow } from "../table";

describe("Table primitives", () => {
  it("TableHead uses caption uppercase tracking", () => {
    render(
      <table>
        <thead>
          <tr>
            <TableHead>RANK</TableHead>
          </tr>
        </thead>
      </table>,
    );
    const th = screen.getByText("RANK");
    expect(th.className).toContain("uppercase");
    expect(th.className).toContain("tracking-[0.16em]");
    expect(th.className).toContain("text-muted");
  });

  it("TableRow has hairline-soft border-b only (no zebra)", () => {
    render(
      <table>
        <TableBody>
          <TableRow data-testid="r">
            <TableCell>x</TableCell>
          </TableRow>
        </TableBody>
      </table>,
    );
    const row = screen.getByTestId("r");
    expect(row.className).toContain("border-b");
    expect(row.className).toContain("border-hairline-soft");
    expect(row.className).not.toContain("hover:bg-muted");
  });

  it("TableCell uses tabular-nums for numeric columns", () => {
    render(
      <table>
        <tbody>
          <tr>
            <TableCell numeric>85</TableCell>
          </tr>
        </tbody>
      </table>,
    );
    const cell = screen.getByText("85");
    expect(cell.className).toContain("tabular-nums");
    expect(cell.className).toContain("font-mono");
  });

  it("DataCard renders the mobile card surface helper", () => {
    render(<DataCard data-testid="mobile-row">移动端行</DataCard>);
    const card = screen.getByTestId("mobile-row");
    expect(card.className).toContain("rounded-md");
    expect(card.className).toContain("border-hairline");
    expect(card.className).toContain("bg-canvas");
    expect(card.className).toContain("shadow-card");
  });
});
