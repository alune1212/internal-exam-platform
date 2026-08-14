/**
 * Declarative coverage inventory for the visual-system browser checks.
 *
 * This file intentionally contains no route interception or API fixtures. The
 * visual suite can consume the same route/state vocabulary while keeping its
 * mutable builders in a separate fixture module.
 */

export type VisualRouteFamily = "candidate" | "admin" | "auth" | "focus";

export type VisualAuthRequirement = "none" | "candidate" | "admin" | "attempt";

export type VisualBrowserState =
  | "ready"
  | "loading"
  | "empty"
  | "error"
  | "validation"
  | "stale"
  | "saving"
  | "saved"
  | "offline"
  | "conflict"
  | "submit"
  | "submitted"
  | "auto-submitted";

export type VisualViewportName =
  | "phone-small"
  | "phone"
  | "phone-wide"
  | "phone-xl"
  | "tablet"
  | "desktop"
  | "landscape-tablet"
  | "landscape-phone";

export type VisualRouteStateEntry = {
  family: VisualRouteFamily;
  route: string;
  auth: VisualAuthRequirement;
  states: readonly VisualBrowserState[];
  signals: readonly string[];
};

export const VISUAL_SYSTEM_VIEWPORTS = [
  { name: "phone-small", width: 320, height: 844 },
  { name: "phone", width: 375, height: 812 },
  { name: "phone-wide", width: 414, height: 896 },
  { name: "phone-xl", width: 430, height: 932 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1280, height: 900 },
  { name: "landscape-tablet", width: 896, height: 414 },
  { name: "landscape-phone", width: 844, height: 390 },
] as const satisfies ReadonlyArray<{
  name: VisualViewportName;
  width: number;
  height: number;
}>;

export const VISUAL_SYSTEM_SPOT_CHECKS = ["zoom-200", "reduced-motion"] as const;

export const ROUTE_STATE_INVENTORY = [
  {
    family: "auth",
    route: "/login",
    auth: "none",
    states: ["ready", "loading", "validation", "error"],
    signals: ["auth-canvas", "no-product-navigation", "no-global-footer", "single-h1"],
  },
  {
    family: "auth",
    route: "/register",
    auth: "none",
    states: ["ready", "loading", "validation", "error"],
    signals: ["auth-canvas", "no-product-navigation", "no-global-footer", "primary-action"],
  },
  {
    family: "auth",
    route: "/admin/login",
    auth: "none",
    states: ["ready", "loading", "validation", "error"],
    signals: ["auth-canvas", "no-product-navigation", "no-global-footer", "single-h1"],
  },
  {
    family: "candidate",
    route: "/learning",
    auth: "candidate",
    states: ["ready", "loading", "empty", "error"],
    signals: ["candidate-top-nav", "single-h1", "primary-action"],
  },
  {
    family: "candidate",
    route: "/practice",
    auth: "candidate",
    states: ["ready", "loading", "empty", "error"],
    signals: ["candidate-top-nav", "focus-question", "submit-action"],
  },
  {
    family: "candidate",
    route: "/practice/wrong-questions",
    auth: "candidate",
    states: ["ready", "loading", "empty", "error"],
    signals: ["candidate-top-nav", "filter", "review-action"],
  },
  {
    family: "candidate",
    route: "/exams",
    auth: "candidate",
    states: ["ready", "loading", "empty", "error"],
    signals: ["candidate-top-nav", "exam-list", "primary-action"],
  },
  {
    family: "candidate",
    route: "/exams/:examId/start",
    auth: "candidate",
    states: ["ready", "loading", "error"],
    signals: ["candidate-top-nav", "exam-rules", "start-action"],
  },
  {
    family: "candidate",
    route: "/exams/:examId/result?attemptId=:attemptId",
    auth: "candidate",
    states: ["ready", "loading", "error"],
    signals: ["candidate-top-nav", "result-summary", "result-filter"],
  },
  {
    family: "candidate",
    route: "/profile",
    auth: "candidate",
    states: ["ready", "loading", "error", "validation", "saved"],
    signals: ["candidate-top-nav", "profile-form", "primary-action"],
  },
  {
    family: "admin",
    route: "/admin/dashboard",
    auth: "admin",
    states: ["ready", "loading", "error"],
    signals: ["admin-navigation", "status-summary", "primary-action"],
  },
  {
    family: "admin",
    route: "/admin/accounts",
    auth: "admin",
    states: ["ready", "loading", "empty", "error", "validation"],
    signals: ["admin-navigation", "filter", "table"],
  },
  {
    family: "admin",
    route: "/admin/questions",
    auth: "admin",
    states: ["ready", "loading", "empty", "error"],
    signals: ["admin-navigation", "filter", "table"],
  },
  {
    family: "admin",
    route: "/admin/questions/import",
    auth: "admin",
    states: ["ready", "loading", "validation", "error"],
    signals: ["admin-navigation", "file-picker", "import-action"],
  },
  {
    family: "admin",
    route: "/admin/exams",
    auth: "admin",
    states: ["ready", "loading", "empty", "error"],
    signals: ["admin-navigation", "exam-list", "primary-action"],
  },
  {
    family: "admin",
    route: "/admin/exams/:examId",
    auth: "admin",
    states: ["ready", "loading", "error", "stale"],
    signals: ["admin-navigation", "exam-context", "workspace-stale", "retry-action"],
  },
  {
    family: "admin",
    route: "/admin/exams/:examId/edit",
    auth: "admin",
    states: ["ready", "loading", "validation", "error"],
    signals: ["admin-navigation", "exam-context", "form", "primary-action"],
  },
  {
    family: "admin",
    route: "/admin/exams/:examId/candidates",
    auth: "admin",
    states: ["ready", "loading", "empty", "validation", "error"],
    signals: ["admin-navigation", "exam-context", "roster", "invitation-action"],
  },
  {
    family: "admin",
    route: "/admin/learning",
    auth: "admin",
    states: ["ready", "loading", "empty", "error"],
    signals: ["admin-navigation", "content-list", "primary-action"],
  },
  {
    family: "admin",
    route: "/admin/learning/reports",
    auth: "admin",
    states: ["ready", "loading", "empty", "error"],
    signals: ["admin-navigation", "filter", "table"],
  },
  {
    family: "admin",
    route: "/admin/reports/scores",
    auth: "admin",
    states: ["ready", "loading", "empty", "error"],
    signals: ["admin-navigation", "filter", "table", "export-action"],
  },
  {
    family: "admin",
    route: "/admin/reports/questions",
    auth: "admin",
    states: ["ready", "loading", "empty", "error"],
    signals: ["admin-navigation", "filter", "table", "export-action"],
  },
  {
    family: "admin",
    route: "/admin/reports/wrong",
    auth: "admin",
    states: ["ready", "loading", "empty", "error"],
    signals: ["admin-navigation", "filter", "table", "export-action"],
  },
  {
    family: "admin",
    route: "/admin/reports/absent",
    auth: "admin",
    states: ["ready", "loading", "empty", "error"],
    signals: ["admin-navigation", "filter", "table", "export-action"],
  },
  {
    family: "admin",
    route: "/admin/operations",
    auth: "admin",
    states: ["ready", "loading", "error"],
    signals: ["admin-navigation", "status-summary", "primary-action"],
  },
  {
    family: "focus",
    route: "/exams/:examId/taking?attemptId=:attemptId",
    auth: "attempt",
    states: [
      "ready",
      "loading",
      "empty",
      "error",
      "saving",
      "saved",
      "offline",
      "conflict",
      "submit",
      "submitted",
      "auto-submitted",
    ],
    signals: ["exam-focus", "timer", "save-status", "navigator", "submit-action"],
  },
  {
    family: "focus",
    route: "/practice?questionId=:questionId",
    auth: "candidate",
    states: ["ready", "loading", "empty", "error", "submit", "submitted"],
    signals: ["exam-focus", "question-options", "submit-action", "feedback"],
  },
] as const satisfies readonly VisualRouteStateEntry[];
