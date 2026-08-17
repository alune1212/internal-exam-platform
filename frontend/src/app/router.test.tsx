import type { RouteObject } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { CANDIDATE_PRESENTATION_HANDLE } from "@/components/layout/candidate-presentation-mode";
import { router } from "@/app/router";
import { ROUTE_STATE_INVENTORY } from "../../e2e/fixtures/route-state-inventory";

function joinPath(parent: string, path: string | undefined) {
  if (!path) return parent || "/";
  if (path.startsWith("/")) return path;
  if (!parent || parent === "/") return `/${path}`;
  return `${parent}/${path}`;
}

function leafPaths(routes: readonly RouteObject[], parent = ""): string[] {
  return routes.flatMap((route) => {
    const path = joinPath(parent, route.path);
    const descendants = route.children ? leafPaths(route.children, path) : [];
    if (route.index) return [path];
    if (route.children) return descendants;
    return [path];
  });
}

describe("application router", () => {
  it("keeps the exact candidate and admin route inventory", () => {
    expect(leafPaths(router.routes)).toEqual([
      "/",
      "/login",
      "/register",
      "/profile",
      "/learning",
      "/learning/:videoId",
      "/practice",
      "/practice/wrong-questions",
      "/exams",
      "/exams/:examId/start",
      "/exams/:examId/taking",
      "/exams/:examId/result",
      "/admin/login",
      "/admin",
      "/admin/dashboard",
      "/admin/accounts",
      "/admin/questions",
      "/admin/questions/import",
      "/admin/exams",
      "/admin/exams/:examId",
      "/admin/exams/:examId/edit",
      "/admin/exams/:examId/candidates",
      "/admin/learning",
      "/admin/learning/reports",
      "/admin/reports/scores",
      "/admin/reports/questions",
      "/admin/reports/wrong",
      "/admin/reports/absent",
      "/admin/operations",
    ]);
  });

  it("declares formal taking as a static Exam Focus route", () => {
    const candidateRoot = router.routes.find((route) => route.path === "/");
    const takingRoute = candidateRoot?.children?.find(
      (route) => route.path === "exams/:examId/taking",
    );

    expect(takingRoute?.handle).toEqual({ [CANDIDATE_PRESENTATION_HANDLE]: "focus" });
  });

  it("keeps every rendered router destination in the visual route/state inventory", () => {
    const redirectOnlyPaths = new Set(["/", "/admin"]);
    const routerDestinations = leafPaths(router.routes).filter(
      (path) => !redirectOnlyPaths.has(path),
    );
    const inventoryDestinations = ROUTE_STATE_INVENTORY.map(({ route }) => route.split("?")[0]);

    expect(new Set(inventoryDestinations)).toEqual(new Set(routerDestinations));
  });
});
