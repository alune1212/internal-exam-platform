import { clearSessionValue, readSessionValue, writeSessionValue } from "@/lib/sessionStorage";

const SESSION_PREFIX = "internal-exam-attempt-session";

export type AttemptSession = {
  candidateId: number;
  attemptId: number;
  credential: string;
  generation: number;
  answerRevision: number;
};

function key(candidateId: number, attemptId: number) {
  return `${SESSION_PREFIX}:${candidateId}:${attemptId}`;
}

export function getAttemptSession(candidateId: number, attemptId: number): AttemptSession | null {
  const raw = readSessionValue(key(candidateId, attemptId));
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<AttemptSession>;
    if (
      parsed.candidateId !== candidateId ||
      parsed.attemptId !== attemptId ||
      typeof parsed.credential !== "string" ||
      !parsed.credential ||
      !Number.isInteger(parsed.generation) ||
      !Number.isInteger(parsed.answerRevision)
    ) {
      throw new Error("invalid attempt session");
    }
    return parsed as AttemptSession;
  } catch {
    clearSessionValue(key(candidateId, attemptId));
    return null;
  }
}

export function setAttemptSession(session: AttemptSession): void {
  writeSessionValue(key(session.candidateId, session.attemptId), JSON.stringify(session));
}

export function updateAttemptSessionRevision(
  session: AttemptSession,
  answerRevision: number,
): AttemptSession {
  const updated = { ...session, answerRevision };
  setAttemptSession(updated);
  return updated;
}

export function clearAttemptSession(candidateId: number, attemptId: number): void {
  clearSessionValue(key(candidateId, attemptId));
}

export function clearAllAttemptSessions(): void {
  for (let index = window.sessionStorage.length - 1; index >= 0; index -= 1) {
    const storageKey = window.sessionStorage.key(index);
    if (storageKey?.startsWith(`${SESSION_PREFIX}:`)) {
      window.sessionStorage.removeItem(storageKey);
    }
  }
}
