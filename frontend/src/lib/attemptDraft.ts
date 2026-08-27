import type { AttemptSession } from "@/lib/attemptSession";

const DRAFT_PREFIX = "internal-exam-attempt-draft";

export type AttemptDraft = {
  candidateId: number;
  attemptId: number;
  generation: number;
  baseRevision: number;
  answers: Record<number, string>;
  updatedAt: string;
};

function key(candidateId: number, attemptId: number) {
  return `${DRAFT_PREFIX}:${candidateId}:${attemptId}`;
}

function readSessionValue(key: string): string | null {
  const sessionValue = window.sessionStorage.getItem(key);
  if (sessionValue) {
    return sessionValue;
  }
  const legacyValue = window.localStorage.getItem(key);
  if (!legacyValue) {
    return null;
  }
  window.sessionStorage.setItem(key, legacyValue);
  window.localStorage.removeItem(key);
  return legacyValue;
}

function writeSessionValue(key: string, value: string): void {
  window.sessionStorage.setItem(key, value);
}

function clearSessionValue(key: string): void {
  window.sessionStorage.removeItem(key);
  window.localStorage.removeItem(key);
}

export function writeAttemptDraft(
  session: AttemptSession,
  answers: Record<number, string>,
): AttemptDraft {
  const draft: AttemptDraft = {
    candidateId: session.candidateId,
    attemptId: session.attemptId,
    generation: session.generation,
    baseRevision: session.answerRevision,
    answers,
    updatedAt: new Date().toISOString(),
  };
  writeSessionValue(key(session.candidateId, session.attemptId), JSON.stringify(draft));
  return draft;
}

export function readMatchingAttemptDraft(
  session: AttemptSession,
  serverRevision: number,
): AttemptDraft | null {
  const raw = readSessionValue(key(session.candidateId, session.attemptId));
  if (!raw) return null;
  try {
    const draft = JSON.parse(raw) as AttemptDraft;
    if (
      draft.candidateId !== session.candidateId ||
      draft.attemptId !== session.attemptId ||
      draft.generation !== session.generation ||
      draft.baseRevision !== serverRevision ||
      !draft.answers ||
      Array.isArray(draft.answers)
    ) {
      return null;
    }
    return draft;
  } catch {
    return null;
  }
}

export function clearAttemptDraft(candidateId: number, attemptId: number): void {
  clearSessionValue(key(candidateId, attemptId));
}

export function clearAllAttemptDrafts(): void {
  for (let index = window.sessionStorage.length - 1; index >= 0; index -= 1) {
    const storageKey = window.sessionStorage.key(index);
    if (storageKey?.startsWith(`${DRAFT_PREFIX}:`)) {
      window.sessionStorage.removeItem(storageKey);
    }
  }
}
