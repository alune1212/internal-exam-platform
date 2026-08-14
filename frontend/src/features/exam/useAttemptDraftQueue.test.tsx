import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { saveAttemptAnswers } from "@/api/attempts";
import { clearAttemptDraft } from "@/lib/attemptDraft";
import type { AttemptSession } from "@/lib/attemptSession";
import { installMockStorage } from "@/test/mockStorage";
import type { Attempt } from "@/types/attempt";

import { useAttemptDraftQueue } from "./useAttemptDraftQueue";

vi.mock("@/api/attempts", () => ({
  saveAttemptAnswers: vi.fn(),
}));

installMockStorage();

const attempt: Attempt = {
  id: 19,
  exam_id: 3,
  candidate_id: 7,
  status: "in_progress",
  started_at: "2026-08-14T00:00:00.000Z",
  duration_minutes: 30,
  ends_at: "2026-08-14T00:30:00.000Z",
  server_now: "2026-08-14T00:01:00.000Z",
  score: 0,
  total_score: 2,
  correct_count: 0,
  wrong_count: 0,
  attempt_session_generation: 1,
  answer_revision: 0,
  questions: [
    {
      id: 101,
      question_type: "single",
      stem_snapshot: "题目",
      options_snapshot: [
        { label: "A", content: "选项 A", sort_order: 1 },
        { label: "B", content: "选项 B", sort_order: 2 },
      ],
      score: 2,
      sort_order: 1,
      selected_answer: "A",
    },
  ],
};

const session: AttemptSession = {
  candidateId: 7,
  attemptId: 19,
  credential: "credential",
  generation: 1,
  answerRevision: 0,
};

function setOnline(value: boolean) {
  Object.defineProperty(window.navigator, "onLine", {
    configurable: true,
    value,
  });
}

describe("useAttemptDraftQueue lifecycle recovery", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    clearAttemptDraft(session.candidateId, session.attemptId);
    setOnline(true);
    vi.clearAllMocks();
    vi.mocked(saveAttemptAnswers).mockResolvedValue({
      saved_count: 1,
      saved_at: "2026-08-14T00:02:00.000Z",
      answer_revision: 1,
    });
  });

  it("reports offline immediately and retries the serialized draft when online", async () => {
    setOnline(false);
    const { result } = renderHook(() => useAttemptDraftQueue(attempt, session));

    act(() => result.current.updateAnswers({ 101: "B" }));

    expect(result.current.saveStatus).toBe("offline");
    expect(result.current.hasUnsynchronizedWork).toBe(true);
    expect(window.sessionStorage.getItem("internal-exam-attempt-draft:7:19")).toContain(
      '"101":"B"',
    );
    expect(saveAttemptAnswers).not.toHaveBeenCalled();

    setOnline(true);
    act(() => window.dispatchEvent(new Event("online")));

    await waitFor(() => expect(saveAttemptAnswers).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(result.current.saveStatus).toBe("saved"));
    expect(result.current.hasUnsynchronizedWork).toBe(false);
  });

  it("persists and best-effort saves the latest draft on page exit", async () => {
    setOnline(false);
    const { result } = renderHook(() => useAttemptDraftQueue(attempt, session));

    act(() => result.current.updateAnswers({ 101: "B" }));
    expect(result.current.isUnsynchronized).toBe(true);

    setOnline(true);
    act(() => window.dispatchEvent(new Event("pagehide")));

    await waitFor(() => expect(saveAttemptAnswers).toHaveBeenCalledTimes(1));
    expect(saveAttemptAnswers).toHaveBeenCalledWith(
      "19",
      "credential",
      [{ attempt_question_id: 101, selected_answer: "B" }],
      0,
    );
  });
});
