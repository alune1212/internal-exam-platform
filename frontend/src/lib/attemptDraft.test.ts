import { beforeEach, describe, expect, it, vi } from "vitest";

import { clearAttemptDraft, readMatchingAttemptDraft, writeAttemptDraft } from "@/lib/attemptDraft";
import type { AttemptSession } from "@/lib/attemptSession";
import { installMockStorage } from "@/test/mockStorage";

installMockStorage();

const session: AttemptSession = {
  candidateId: 7,
  attemptId: 19,
  credential: "credential",
  generation: 2,
  answerRevision: 4,
};

describe("attemptDraft", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.useRealTimers();
  });

  it("restores only the matching candidate attempt generation and server revision", () => {
    writeAttemptDraft(session, { 101: "A", 102: "A,C" });

    expect(readMatchingAttemptDraft(session, 4)?.answers).toEqual({ 101: "A", 102: "A,C" });
    expect(readMatchingAttemptDraft({ ...session, generation: 3 }, 4)).toBeNull();
    expect(readMatchingAttemptDraft(session, 5)).toBeNull();
  });

  it("clears a synchronized draft", () => {
    writeAttemptDraft(session, { 101: "B" });

    clearAttemptDraft(session.candidateId, session.attemptId);

    expect(readMatchingAttemptDraft(session, 4)).toBeNull();
  });
});
