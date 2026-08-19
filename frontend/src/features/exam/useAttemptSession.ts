import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";

import { getAttempt, takeoverAttempt } from "@/api/attempts";
import { ApiError } from "@/api/client";
import { clearAttemptDraft } from "@/lib/attemptDraft";
import {
  clearAttemptSession,
  getAttemptSession,
  setAttemptSession,
  type AttemptSession,
} from "@/lib/attemptSession";

function isAttemptSessionConflict(error: unknown) {
  return (
    error instanceof ApiError &&
    error.status === 409 &&
    (error.detail?.includes("考试会话已失效") ?? false)
  );
}

export function useAttemptSession(candidateId: number | null, attemptId: string | null) {
  const numericAttemptId = Number(attemptId);
  const hasScope = candidateId !== null && Number.isInteger(numericAttemptId);
  const [session, setSessionState] = useState<AttemptSession | null>(() =>
    candidateId !== null && Number.isInteger(numericAttemptId)
      ? getAttemptSession(candidateId, numericAttemptId)
      : null,
  );
  const [sessionConflict, setSessionConflict] = useState(false);

  useEffect(() => {
    // The initializer already reads from storage on mount; here we only
    // clear any leftover conflict state when the scope changes.
    setSessionConflict(false);
  }, [candidateId, numericAttemptId]);

  const invalidateSession = useCallback(() => {
    if (candidateId !== null && Number.isInteger(numericAttemptId)) {
      clearAttemptSession(candidateId, numericAttemptId);
      clearAttemptDraft(candidateId, numericAttemptId);
    }
    setSessionState(null);
    setSessionConflict(true);
  }, [candidateId, numericAttemptId]);

  const replaceSession = useCallback((nextSession: AttemptSession) => {
    setAttemptSession(nextSession);
    setSessionState(nextSession);
    setSessionConflict(false);
  }, []);

  const attemptQuery = useQuery({
    queryKey: ["candidate", candidateId, "attempt", attemptId, session?.generation],
    queryFn: () => getAttempt(attemptId ?? "", session?.credential ?? ""),
    enabled: Boolean(hasScope && session),
    retry: false,
  });

  useEffect(() => {
    if (isAttemptSessionConflict(attemptQuery.error)) {
      invalidateSession();
    }
  }, [attemptQuery.error, invalidateSession]);

  const takeoverMutation = useMutation({
    mutationFn: () => takeoverAttempt(attemptId ?? ""),
    onSuccess: (result) => {
      if (candidateId === null) return;
      clearAttemptDraft(candidateId, result.attempt_id);
      replaceSession({
        candidateId,
        attemptId: result.attempt_id,
        credential: result.attempt_session_credential,
        generation: result.attempt_session_generation,
        answerRevision: result.answer_revision,
      });
    },
    retry: false,
  });

  return {
    ...attemptQuery,
    session,
    sessionConflict,
    replaceSession,
    invalidateSession,
    takeover: takeoverMutation.mutate,
    takeoverError: takeoverMutation.error,
    takeoverPending: takeoverMutation.isPending,
  };
}
