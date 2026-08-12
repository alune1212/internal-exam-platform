import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { TopNav } from "@/components/layout/TopNav";
import { PageState } from "@/components/page";
import { detectBrowserSupport } from "@/lib/browserSupport";
import {
  clearCurrentCandidate,
  getCurrentCandidate,
  setCurrentCandidate,
  getSafeReturnTo,
} from "@/lib/candidateSession";
import { subscribeSessionChanges } from "@/lib/sessionEvents";
import { cn } from "@/lib/utils";
import type { Candidate } from "@/types/candidate";

export type CandidateSessionContext = {
  candidate: Candidate | null;
  loginCandidate: (candidate: Candidate) => void;
  logoutCandidate: () => void;
};

export function CandidateLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [candidate, setCandidate] = useState<Candidate | null>(() => getCurrentCandidate());
  const isAuthRoute = location.pathname === "/login" || location.pathname === "/register";
  const browserSupport = detectBrowserSupport(window.navigator.userAgent);

  useEffect(() => {
    return subscribeSessionChanges((event) => {
      if (event.reason === "candidate-login") {
        setCandidate(getCurrentCandidate());
      } else if (event.reason === "candidate-logout" || event.reason === "unauthorized") {
        setCandidate(null);
      }
    });
  }, []);

  if (!browserSupport.supported) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas-warm px-4 py-8">
        <div className="w-full max-w-xl rounded-lg border border-error bg-canvas p-8 shadow-pop">
          <PageState
            state="error"
            eyebrow="DEVICE · 浏览器不受支持"
            title="请更换受支持的系统浏览器。"
            description={browserSupport.reason}
          />
          <p className="mt-4 text-body-sm text-muted">
            支持 Windows Edge/Chrome、macOS Chrome/Safari（Chrome 120+、Safari 17+）、Android Chrome
            和 iOS Safari；微信等内嵌浏览器不能用于正式考试。
          </p>
        </div>
      </main>
    );
  }

  if (!candidate && !isAuthRoute) {
    const currentTarget = `${location.pathname}${location.search}${location.hash}`;
    const returnTo = getSafeReturnTo(currentTarget);
    return <Navigate to={`/login?returnTo=${encodeURIComponent(returnTo)}`} replace />;
  }

  function loginCandidate(nextCandidate: Candidate) {
    setCurrentCandidate(nextCandidate);
  }

  function logoutCandidate() {
    clearCurrentCandidate();
    navigate("/login", { replace: true });
  }

  return (
    <div className={cn("flex min-h-screen flex-col bg-canvas", isAuthRoute && "bg-canvas-warm")}>
      {isAuthRoute ? null : <TopNav candidate={candidate} onLogout={logoutCandidate} />}
      <main
        className={cn(
          "w-full flex-1",
          isAuthRoute
            ? "flex min-h-screen items-center justify-center px-4 py-8 md:px-6"
            : "mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-10",
        )}
      >
        <Outlet
          context={{ candidate, loginCandidate, logoutCandidate } satisfies CandidateSessionContext}
        />
      </main>
    </div>
  );
}
