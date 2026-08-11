import { useMutation } from "@tanstack/react-query";
import { useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";

import { submitAttempt } from "@/api/attempts";
import { ApiError } from "@/api/client";
import { clearAttemptSession, type AttemptSession } from "@/lib/attemptSession";

function isInvalidAttemptSession(error: unknown) {
  return (
    error instanceof ApiError &&
    error.status === 409 &&
    (error.detail?.includes("考试会话已失效") ?? false)
  );
}

export function useExamSubmission({
  examId,
  attemptId,
  session,
  performFullSave,
  cancelPendingSave,
  clearDraft,
  invalidateSession,
}: {
  examId: string;
  attemptId: string | null;
  session: AttemptSession | null;
  performFullSave: (options?: { throwOnError?: boolean }) => Promise<void>;
  cancelPendingSave: () => void;
  clearDraft: () => void;
  invalidateSession: () => void;
}) {
  const navigate = useNavigate();
  const submitStartedRef = useRef(false);
  const mutation = useMutation({
    mutationFn: async (submitType: "manual" = "manual") => {
      if (!attemptId || !session) return null;
      cancelPendingSave();
      await performFullSave({ throwOnError: true });
      return submitAttempt(attemptId, session.credential, submitType);
    },
    onSuccess: (result) => {
      if (!result || !session) return;
      clearDraft();
      clearAttemptSession(session.candidateId, session.attemptId);
      navigate(`/exams/${examId}/result?attemptId=${result.attempt_id}`);
    },
    onError: (error) => {
      submitStartedRef.current = false;
      if (isInvalidAttemptSession(error)) invalidateSession();
    },
    retry: false,
  });

  const requestSubmit = useCallback(
    (submitType: "manual") => {
      if (submitStartedRef.current || mutation.isPending) return;
      submitStartedRef.current = true;
      mutation.mutate(submitType);
    },
    [mutation],
  );

  return { ...mutation, requestSubmit, submitStartedRef };
}
