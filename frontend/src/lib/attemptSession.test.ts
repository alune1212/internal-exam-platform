import { beforeEach, describe, expect, it } from "vitest";

import {
  clearAllAttemptSessions,
  getAttemptSession,
  setAttemptSession,
  updateAttemptSessionRevision,
} from "@/lib/attemptSession";
import { installMockStorage } from "@/test/mockStorage";

installMockStorage();

describe("attemptSession", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("keeps opaque credentials only in sessionStorage and updates revisions", () => {
    const session = {
      candidateId: 7,
      attemptId: 19,
      credential: "opaque-device-credential",
      generation: 1,
      answerRevision: 0,
    };

    setAttemptSession(session);
    const updated = updateAttemptSessionRevision(session, 2);

    expect(getAttemptSession(7, 19)).toEqual(updated);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.getItem("internal-exam-attempt-session:7:19")).toContain(
      "opaque-device-credential",
    );
  });

  it("rejects mismatched or invalid scoped sessions", () => {
    window.sessionStorage.setItem(
      "internal-exam-attempt-session:7:19",
      JSON.stringify({ candidateId: 8, attemptId: 19, credential: "x" }),
    );

    expect(getAttemptSession(7, 19)).toBeNull();
  });

  it("clears all attempt credentials at candidate logout", () => {
    setAttemptSession({
      candidateId: 7,
      attemptId: 19,
      credential: "one",
      generation: 1,
      answerRevision: 0,
    });
    setAttemptSession({
      candidateId: 8,
      attemptId: 20,
      credential: "two",
      generation: 1,
      answerRevision: 0,
    });

    clearAllAttemptSessions();

    expect(window.sessionStorage.length).toBe(0);
  });
});
