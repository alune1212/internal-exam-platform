import { useEffect, useState } from "react";
import { Navigate, Outlet, useLocation, useMatches, useNavigate } from "react-router-dom";
import { TopNav } from "@/components/layout/TopNav";
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

import {
  CandidatePresentationBoundary,
  hasStaticCandidateFocus,
  useCandidatePresentationMode,
} from "./candidate-presentation-mode";
import { UnsupportedBrowserNotice } from "./UnsupportedBrowserNotice";

export type CandidateSessionContext = {
  candidate: Candidate | null;
  loginCandidate: (candidate: Candidate) => void;
  logoutCandidate: () => void;
};

function CandidateLayoutFrame({
  candidate,
  isAuthRoute,
  loginCandidate,
  logoutCandidate,
}: {
  candidate: Candidate | null;
  isAuthRoute: boolean;
  loginCandidate: (candidate: Candidate) => void;
  logoutCandidate: () => void;
}) {
  const { mode } = useCandidatePresentationMode();
  const showCandidateChrome = !isAuthRoute && mode !== "focus";

  return (
    <div
      data-testid="candidate-layout-frame"
      data-candidate-presentation={mode}
      className={cn("flex min-h-screen flex-col bg-canvas", isAuthRoute && "bg-canvas-warm")}
    >
      {showCandidateChrome ? <TopNav candidate={candidate} onLogout={logoutCandidate} /> : null}
      <main
        className={cn(
          "w-full min-w-0 flex-1",
          isAuthRoute
            ? "flex min-h-screen items-center justify-center px-page-inline py-page-block md:px-page-inline-lg"
            : "",
        )}
      >
        <Outlet
          context={{ candidate, loginCandidate, logoutCandidate } satisfies CandidateSessionContext}
        />
      </main>
    </div>
  );
}

export function CandidateLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const matches = useMatches();
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
    return <UnsupportedBrowserNotice support={browserSupport} />;
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

  const initialPresentationMode = isAuthRoute
    ? "auth"
    : hasStaticCandidateFocus(matches)
      ? "focus"
      : "calm";

  return (
    <CandidatePresentationBoundary initialMode={initialPresentationMode}>
      <CandidateLayoutFrame
        candidate={candidate}
        isAuthRoute={isAuthRoute}
        loginCandidate={loginCandidate}
        logoutCandidate={logoutCandidate}
      />
    </CandidatePresentationBoundary>
  );
}
