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

  it("does not promote a legacy localStorage draft", () => {
    window.localStorage.setItem(
      "internal-exam-attempt-draft:7:19",
      JSON.stringify({
        candidateId: 7,
        attemptId: 19,
        generation: 2,
        baseRevision: 4,
        answers: { 101: "A" },
        updatedAt: new Date().toISOString(),
      }),
    );

    expect(readMatchingAttemptDraft(session, 4)).toBeNull();
    expect(window.localStorage.getItem("internal-exam-attempt-draft:7:19")).toContain('"101":"A"');
  });

  it("clears a synchronized draft", () => {
    writeAttemptDraft(session, { 101: "B" });

    clearAttemptDraft(session.candidateId, session.attemptId);

    expect(readMatchingAttemptDraft(session, 4)).toBeNull();
  });
});
