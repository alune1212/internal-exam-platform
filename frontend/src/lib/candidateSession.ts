import type { Candidate } from "@/types/candidate";

const STORAGE_KEY = "internal-exam-candidate";

export function getCurrentCandidate(): Candidate | null {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as Candidate;
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function setCurrentCandidate(candidate: Candidate) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(candidate));
}

export function clearCurrentCandidate() {
  window.localStorage.removeItem(STORAGE_KEY);
}
