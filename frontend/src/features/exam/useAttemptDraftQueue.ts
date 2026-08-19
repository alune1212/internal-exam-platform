import { useCallback, useEffect, useRef, useState } from "react";

import { saveAttemptAnswers } from "@/api/attempts";
import { ApiError } from "@/api/client";
import { clearAttemptDraft, readMatchingAttemptDraft, writeAttemptDraft } from "@/lib/attemptDraft";
import { updateAttemptSessionRevision, type AttemptSession } from "@/lib/attemptSession";
import type { AnswerSaveItem, Attempt } from "@/types/attempt";

export type AnswerMap = Record<number, string>;
export type SaveStatus = "saved" | "pending" | "saving" | "offline" | "conflict" | "error";

const SAVE_DEBOUNCE_MS = 150;

function classifySaveFailure(error: unknown): SaveStatus {
  if (error instanceof ApiError) {
    return error.status === 409 ? "conflict" : "error";
  }
  return "offline";
}

function isBrowserOffline(): boolean {
  return typeof navigator !== "undefined" && navigator.onLine === false;
}

export function useAttemptDraftQueue(attempt: Attempt | undefined, session: AttemptSession | null) {
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [saveStatus, setSaveStatusState] = useState<SaveStatus>("saved");
  const [hasUnsynchronizedWork, setHasUnsynchronizedWorkState] = useState(false);
  const answersRef = useRef<AnswerMap>({});
  const sessionRef = useRef<AttemptSession | null>(session);
  const saveStatusRef = useRef<SaveStatus>("saved");
  const hasUnsynchronizedWorkRef = useRef(false);
  const changeVersionRef = useRef(0);
  const saveQueueRef = useRef<Promise<void>>(Promise.resolve());
  const saveDebounceRef = useRef<number | null>(null);

  const setSaveStatus = useCallback((status: SaveStatus) => {
    saveStatusRef.current = status;
    setSaveStatusState(status);
  }, []);

  const setHasUnsynchronizedWork = useCallback((value: boolean) => {
    hasUnsynchronizedWorkRef.current = value;
    setHasUnsynchronizedWorkState(value);
  }, []);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  const cancelPendingSave = useCallback(() => {
    if (saveDebounceRef.current !== null) {
      window.clearTimeout(saveDebounceRef.current);
      saveDebounceRef.current = null;
    }
  }, []);

  const buildAnswerItems = useCallback((): AnswerSaveItem[] => {
    if (!attempt) return [];
    return attempt.questions.map((question) => ({
      attempt_question_id: question.id,
      selected_answer: answersRef.current[question.id] ?? "",
    }));
  }, [attempt]);

  const runSave = useCallback(async () => {
    const activeSession = sessionRef.current;
    if (!attempt || !activeSession) return;
    const savedChangeVersion = changeVersionRef.current;
    setHasUnsynchronizedWork(true);
    if (isBrowserOffline()) {
      setSaveStatus("offline");
      throw new Error("offline");
    }
    setSaveStatus("saving");
    try {
      const result = await saveAttemptAnswers(
        String(attempt.id),
        activeSession.credential,
        buildAnswerItems(),
        activeSession.answerRevision,
      );
      const updatedSession = updateAttemptSessionRevision(activeSession, result.answer_revision);
      sessionRef.current = updatedSession;
      if (changeVersionRef.current === savedChangeVersion) {
        clearAttemptDraft(activeSession.candidateId, activeSession.attemptId);
        setHasUnsynchronizedWork(false);
        setSaveStatus("saved");
      } else {
        writeAttemptDraft(updatedSession, answersRef.current);
        setHasUnsynchronizedWork(true);
        setSaveStatus("pending");
      }
    } catch (error) {
      setSaveStatus(classifySaveFailure(error));
      throw error;
    }
  }, [attempt, buildAnswerItems, setHasUnsynchronizedWork, setSaveStatus]);

  const performFullSave = useCallback(
    async ({ throwOnError = false }: { throwOnError?: boolean } = {}) => {
      const run = saveQueueRef.current.catch(() => undefined).then(runSave);
      saveQueueRef.current = run.catch(() => undefined);
      try {
        await run;
      } catch (error) {
        if (throwOnError) throw error;
      }
    },
    [runSave],
  );

  const scheduleFullSave = useCallback(() => {
    if (!attempt || !sessionRef.current) return;
    setHasUnsynchronizedWork(true);
    setSaveStatus(isBrowserOffline() ? "offline" : "pending");
    cancelPendingSave();
    if (isBrowserOffline()) return;
    saveDebounceRef.current = window.setTimeout(() => {
      saveDebounceRef.current = null;
      void performFullSave();
    }, SAVE_DEBOUNCE_MS);
  }, [attempt, cancelPendingSave, performFullSave, setHasUnsynchronizedWork, setSaveStatus]);

  const updateAnswers = useCallback(
    (nextAnswers: AnswerMap) => {
      const activeSession = sessionRef.current;
      answersRef.current = nextAnswers;
      setAnswers(nextAnswers);
      changeVersionRef.current += 1;
      if (activeSession) {
        writeAttemptDraft(activeSession, nextAnswers);
      }
      scheduleFullSave();
    },
    [scheduleFullSave],
  );

  useEffect(() => {
    if (!attempt || !session) return;
    const synchronizedSession =
      session.answerRevision === attempt.answer_revision
        ? session
        : updateAttemptSessionRevision(session, attempt.answer_revision);
    sessionRef.current = synchronizedSession;

    const serverAnswers = Object.fromEntries(
      attempt.questions.map((question) => [question.id, question.selected_answer ?? ""]),
    );
    const draft = readMatchingAttemptDraft(synchronizedSession, attempt.answer_revision);
    const initialAnswers = draft ? { ...serverAnswers, ...draft.answers } : serverAnswers;
    answersRef.current = initialAnswers;
    setAnswers(initialAnswers);
    setHasUnsynchronizedWork(Boolean(draft));
    setSaveStatus(draft ? (isBrowserOffline() ? "offline" : "pending") : "saved");
    if (draft) {
      changeVersionRef.current += 1;
      cancelPendingSave();
      if (!isBrowserOffline()) {
        saveDebounceRef.current = window.setTimeout(() => {
          saveDebounceRef.current = null;
          void performFullSave();
        }, SAVE_DEBOUNCE_MS);
      }
      return cancelPendingSave;
    }
  }, [
    attempt,
    attempt?.answer_revision,
    attempt?.attempt_session_generation,
    attempt?.id,
    cancelPendingSave,
    performFullSave,
    session,
    setHasUnsynchronizedWork,
    setSaveStatus,
  ]);

  const persistDraftForLifecycle = useCallback(() => {
    const activeSession = sessionRef.current;
    if (!activeSession || !hasUnsynchronizedWorkRef.current) return;
    writeAttemptDraft(activeSession, answersRef.current);
  }, []);

  const retryPendingDraft = useCallback(() => {
    if (!hasUnsynchronizedWorkRef.current) return;
    if (
      saveStatusRef.current === "offline" ||
      saveStatusRef.current === "pending" ||
      saveStatusRef.current === "error"
    ) {
      void performFullSave();
    }
  }, [performFullSave]);

  useEffect(() => {
    function handleOnline() {
      retryPendingDraft();
      if (!hasUnsynchronizedWorkRef.current) setSaveStatus("saved");
    }

    function handleOffline() {
      if (!attempt || !sessionRef.current) return;
      if (saveStatusRef.current !== "conflict") setSaveStatus("offline");
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "hidden") {
        persistDraftForLifecycle();
        // Best effort only: browsers may stop in-flight work after hiding.
        if (hasUnsynchronizedWorkRef.current) void performFullSave();
        return;
      }
      retryPendingDraft();
    }

    function handlePageHide() {
      persistDraftForLifecycle();
      // Keep this an ordinary revisioned request; do not weaken it to beacon.
      if (hasUnsynchronizedWorkRef.current) void performFullSave();
    }

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pagehide", handlePageHide);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("pagehide", handlePageHide);
    };
  }, [attempt, performFullSave, persistDraftForLifecycle, retryPendingDraft, setSaveStatus]);

  const clearDraft = useCallback(() => {
    const activeSession = sessionRef.current;
    cancelPendingSave();
    if (activeSession) {
      clearAttemptDraft(activeSession.candidateId, activeSession.attemptId);
    }
    setHasUnsynchronizedWork(false);
    setSaveStatus("saved");
  }, [cancelPendingSave, setHasUnsynchronizedWork, setSaveStatus]);

  return {
    answers,
    answersRef,
    saveStatus,
    hasUnsynchronizedWork,
    isUnsynchronized: hasUnsynchronizedWork,
    updateAnswers,
    performFullSave,
    cancelPendingSave,
    clearDraft,
  };
}
