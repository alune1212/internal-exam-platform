import { describe, expect, it } from "vitest";

import { emitSessionChanged } from "@/lib/sessionEvents";
import { bindSessionCacheClearing, createAppQueryClient } from "./queryClient";

describe("createAppQueryClient", () => {
  it("sets conservative default query behavior for admin and candidate pages", () => {
    const queryClient = createAppQueryClient();
    const defaults = queryClient.getDefaultOptions();

    expect(defaults.queries?.staleTime).toBe(30_000);
    expect(defaults.queries?.retry).toBe(1);
    expect(defaults.queries?.refetchOnWindowFocus).toBe(false);
  });

  it("clears all cached data when the active identity changes", () => {
    const queryClient = createAppQueryClient();
    const unsubscribe = bindSessionCacheClearing(queryClient);
    queryClient.setQueryData(["admin", "exams"], [{ id: 1 }]);
    queryClient.setQueryData(["candidate", 1, "attempt", 10], { id: 10 });

    emitSessionChanged({ reason: "candidate-login" });

    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    unsubscribe();
  });
});
