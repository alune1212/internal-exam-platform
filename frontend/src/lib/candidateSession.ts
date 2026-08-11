import { clearSessionValue, readSessionValue, writeSessionValue } from "@/lib/sessionStorage";
import { emitSessionChanged } from "@/lib/sessionEvents";
import type { Candidate } from "@/types/candidate";
import { clearAllAttemptSessions } from "@/lib/attemptSession";
import { clearAllAttemptDrafts } from "@/lib/attemptDraft";

const STORAGE_KEY = "internal-exam-candidate";

export function getCurrentCandidate(): Candidate | null {
  const raw = readSessionValue(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  return parseCandidate(raw);
}

function parseCandidate(raw: string): Candidate | null {
  try {
    return JSON.parse(raw) as Candidate;
  } catch {
    clearSessionValue(STORAGE_KEY);
    return null;
  }
}

export function setCurrentCandidate(candidate: Candidate) {
  writeSessionValue(STORAGE_KEY, JSON.stringify(candidate));
  emitSessionChanged({ reason: "candidate-login" });
}

export function clearCurrentCandidate(
  reason: "candidate-logout" | "unauthorized" = "candidate-logout",
) {
  clearSessionValue(STORAGE_KEY);
  clearAllAttemptSessions();
  clearAllAttemptDrafts();
  emitSessionChanged({ reason });
}
