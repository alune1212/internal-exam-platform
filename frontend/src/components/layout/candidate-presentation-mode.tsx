import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import type { UIMatch } from "react-router-dom";

export type CandidatePresentationMode = "auth" | "calm" | "focus";

type CandidatePresentationContextValue = {
  mode: CandidatePresentationMode;
  requestPresentationMode: (mode: "focus") => () => void;
};

const CandidatePresentationContext = createContext<CandidatePresentationContextValue | null>(null);

/**
 * Route metadata is the static boundary for specialized candidate chrome.
 * Keep this key in one place so a route cannot silently invent another shell
 * contract.
 */
export const CANDIDATE_PRESENTATION_HANDLE = "candidatePresentationMode" as const;

type CandidateRouteHandle = {
  [CANDIDATE_PRESENTATION_HANDLE]?: CandidatePresentationMode;
};

// eslint-disable-next-line react-refresh/only-export-components
export function hasStaticCandidateFocus(matches: readonly UIMatch[]) {
  return matches.some((match) => {
    const handle = match.handle as CandidateRouteHandle | undefined;
    return handle?.[CANDIDATE_PRESENTATION_HANDLE] === "focus";
  });
}

export function CandidatePresentationBoundary({
  initialMode = "calm",
  children,
}: {
  initialMode?: CandidatePresentationMode;
  children: ReactNode;
}) {
  const nextRequestId = useRef(0);
  const [focusRequests, setFocusRequests] = useState<ReadonlySet<number>>(() => new Set());

  const requestPresentationMode = useCallback((mode: "focus") => {
    if (mode !== "focus") return () => undefined;
    const requestId = nextRequestId.current++;
    setFocusRequests((current) => new Set(current).add(requestId));

    let released = false;
    return () => {
      if (released) return;
      released = true;
      setFocusRequests((current) => {
        if (!current.has(requestId)) return current;
        const next = new Set(current);
        next.delete(requestId);
        return next;
      });
    };
  }, []);

  const mode: CandidatePresentationMode =
    initialMode === "focus" || focusRequests.size > 0 ? "focus" : initialMode;

  return (
    <CandidatePresentationContext.Provider value={{ mode, requestPresentationMode }}>
      {children}
    </CandidatePresentationContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCandidatePresentationMode(): CandidatePresentationContextValue {
  const context = useContext(CandidatePresentationContext);
  if (context) return context;

  // Pages are also rendered in focused unit tests without the application
  // shell. They retain ordinary presentation in that isolated environment.
  return {
    mode: "calm",
    requestPresentationMode: () => () => undefined,
  };
}
