import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";

import { Footer } from "@/components/layout/Footer";
import { TopNav } from "@/components/layout/TopNav";
import {
  clearCurrentCandidate,
  getCurrentCandidate,
  setCurrentCandidate,
} from "@/lib/candidateSession";
import type { Candidate } from "@/types/candidate";

export type CandidateSessionContext = {
  candidate: Candidate | null;
  loginCandidate: (candidate: Candidate) => void;
  logoutCandidate: () => void;
};

export function CandidateLayout() {
  const navigate = useNavigate();
  const [candidate, setCandidate] = useState<Candidate | null>(() => getCurrentCandidate());

  function loginCandidate(nextCandidate: Candidate) {
    setCurrentCandidate(nextCandidate);
    setCandidate(nextCandidate);
  }

  function logoutCandidate() {
    clearCurrentCandidate();
    setCandidate(null);
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <TopNav candidate={candidate} onLogout={logoutCandidate} />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-8 md:py-10">
        <Outlet
          context={{ candidate, loginCandidate, logoutCandidate } satisfies CandidateSessionContext}
        />
      </main>
      <Footer />
    </div>
  );
}
