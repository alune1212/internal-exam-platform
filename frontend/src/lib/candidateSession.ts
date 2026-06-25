import type { Candidate } from "@/types/candidate";
import { emitSessionChanged } from "@/lib/sessionEvents";

const STORAGE_KEY = "internal-exam-candidate";

export function getCurrentCandidate(): Candidate | null {
  const raw = window.sessionStorage.getItem(STORAGE_KEY);
  if (!raw) {
    const legacyRaw = window.localStorage.getItem(STORAGE_KEY);
    if (!legacyRaw) {
      return null;
    }
    window.sessionStorage.setItem(STORAGE_KEY, legacyRaw);
    window.localStorage.removeItem(STORAGE_KEY);
    return parseCandidate(legacyRaw);
  }
  return parseCandidate(raw);
}

function parseCandidate(raw: string): Candidate | null {
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as Candidate;
  } catch {
    window.sessionStorage.removeItem(STORAGE_KEY);
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function setCurrentCandidate(candidate: Candidate) {
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(candidate));
  window.localStorage.removeItem(STORAGE_KEY);
  emitSessionChanged({ reason: "candidate-login" });
}

export function clearCurrentCandidate(
  reason: "candidate-logout" | "unauthorized" = "candidate-logout",
) {
  window.sessionStorage.removeItem(STORAGE_KEY);
  window.localStorage.removeItem(STORAGE_KEY);
  emitSessionChanged({ reason });
}
