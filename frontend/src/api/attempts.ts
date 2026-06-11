import { apiRequest } from "@/api/client";
import type { Attempt, AttemptResult } from "@/types/attempt";

export function getAttempt(attemptId: string) {
  return apiRequest<Attempt>(`/api/attempts/${attemptId}`);
}

export function getAttemptResult(attemptId: string) {
  return apiRequest<AttemptResult>(`/api/attempts/${attemptId}/result`);
}
