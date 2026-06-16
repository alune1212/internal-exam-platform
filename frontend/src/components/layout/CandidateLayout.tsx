import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";

import { getActiveExams } from "@/api/exams";
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
  const activeExams = useQuery({ queryKey: ["active-exams"], queryFn: getActiveExams });
  const activeExamId = activeExams.data?.[0]?.id ?? null;

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
      <TopNav candidate={candidate} onLogout={logoutCandidate} activeExamId={activeExamId} />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-8 md:py-10">
        <Outlet
          context={{ candidate, loginCandidate, logoutCandidate } satisfies CandidateSessionContext}
        />
      </main>
      <Footer />
    </div>
  );
}
