import { describe, expect, it } from "vitest";

import { createAppQueryClient } from "./queryClient";

describe("createAppQueryClient", () => {
  it("sets conservative default query behavior for admin and candidate pages", () => {
    const queryClient = createAppQueryClient();
    const defaults = queryClient.getDefaultOptions();

    expect(defaults.queries?.staleTime).toBe(30_000);
    expect(defaults.queries?.retry).toBe(1);
    expect(defaults.queries?.refetchOnWindowFocus).toBe(false);
  });
});
