import { apiRequest } from "@/api/client";
import type {
  AnswerSaveItem,
  AnswerSaveResponse,
  Attempt,
  AttemptResult,
  AttemptSessionTakeover,
} from "@/types/attempt";

function attemptSessionHeaders(credential: string) {
  return { "X-Attempt-Session": credential };
}

export function getAttempt(attemptId: string, credential: string) {
  return apiRequest<Attempt>(`/api/attempts/${attemptId}`, {
    headers: attemptSessionHeaders(credential),
  });
}

export function getAttemptResult(attemptId: string) {
  return apiRequest<AttemptResult>(`/api/attempts/${attemptId}/result`);
}

export function saveAttemptAnswers(
  attemptId: string,
  credential: string,
  answers: AnswerSaveItem[],
  answerRevision: number,
) {
  return apiRequest<AnswerSaveResponse>(`/api/attempts/${attemptId}/answers/save`, {
    method: "POST",
    headers: attemptSessionHeaders(credential),
    body: JSON.stringify({ answers, answer_revision: answerRevision }),
  });
}

export function submitAttempt(
  attemptId: string,
  credential: string,
  submitType: "manual" = "manual",
) {
  return apiRequest<AttemptResult>(`/api/attempts/${attemptId}/submit`, {
    method: "POST",
    headers: attemptSessionHeaders(credential),
    body: JSON.stringify({ submit_type: submitType }),
  });
}

export function takeoverAttempt(attemptId: string) {
  return apiRequest<AttemptSessionTakeover>(`/api/attempts/${attemptId}/takeover`, {
    method: "POST",
  });
}
