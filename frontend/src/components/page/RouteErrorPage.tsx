import { useNavigate, useRouteError } from "react-router-dom";

import { PageShell } from "./PageShell";
import { PageState } from "./PageState";

export interface RouteErrorPageProps {
  /** Override the browser reload in tests or an embedding shell. */
  onReload?: () => void;
  /** Safe destination for a route that cannot be loaded. */
  safePath?: string;
}

function errorDescription(error: unknown): string {
  if (error && typeof error === "object" && "statusText" in error) {
    const statusText = (error as { statusText?: unknown }).statusText;
    if (typeof statusText === "string" && statusText.trim()) {
      return `页面资源暂时不可用（${statusText}），请重试或返回安全入口。`;
    }
  }
  return "页面资源暂时不可用，请重试或返回安全入口。";
}

/**
 * Error element for lazy route/module failures.
 *
 * The reload and home actions are intentionally user-triggered.  In
 * particular, this component never calls reload from an effect, preventing a
 * stale or missing chunk from creating an automatic reload loop.
 */
export function RouteErrorPage({ onReload, safePath = "/" }: RouteErrorPageProps = {}) {
  const routeError = useRouteError();
  const navigate = useNavigate();

  return (
    <PageShell density="calm" className="mx-auto max-w-3xl py-12" data-testid="route-error-page">
      <PageState
        state="error"
        eyebrow="ROUTE · 资源加载"
        title="页面暂时无法打开。"
        description={errorDescription(routeError)}
        onRetry={onReload ?? (() => window.location.reload())}
        retryLabel="重新加载"
        secondaryAction={{ label: "返回首页", onClick: () => navigate(safePath) }}
      />
    </PageShell>
  );
}

// Keep a descriptive alias for callers that treat this as a route error state
// rather than a full page.
export const RouteErrorState = RouteErrorPage;
export const RouteErrorBoundary = RouteErrorPage;
