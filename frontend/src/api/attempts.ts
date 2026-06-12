import { apiRequest } from "@/api/client";
import type { AnswerSaveItem, Attempt, AttemptResult } from "@/types/attempt";

export function getAttempt(attemptId: string) {
  return apiRequest<Attempt>(`/api/attempts/${attemptId}`);
}

export function getAttemptResult(attemptId: string) {
  return apiRequest<AttemptResult>(`/api/attempts/${attemptId}/result`);
}

export function saveAttemptAnswers(attemptId: string, answers: AnswerSaveItem[]) {
  return apiRequest<{ saved_count: number; saved_at: string }>(`/api/attempts/${attemptId}/answers/save`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export function submitAttempt(attemptId: string, submitType: "manual" | "auto" = "manual") {
  return apiRequest<AttemptResult>(`/api/attempts/${attemptId}/submit`, {
    method: "POST",
    body: JSON.stringify({ submit_type: submitType }),
  });
}
