import { apiRequest } from "@/api/client";
import type {
  AdminQuestion,
  PracticeAnswerResult,
  PracticeQuestion,
  PracticeWrongQuestion,
  QuestionPayload,
} from "@/types/question";

export function getPracticeQuestions() {
  return apiRequest<PracticeQuestion[]>("/api/practice/questions");
}

export function getAdminQuestions() {
  return apiRequest<AdminQuestion[]>("/api/admin/questions");
}

export function createAdminQuestion(payload: QuestionPayload) {
  return apiRequest<AdminQuestion>("/api/admin/questions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAdminQuestion(questionId: number, payload: Partial<QuestionPayload>) {
  return apiRequest<AdminQuestion>(`/api/admin/questions/${questionId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteAdminQuestion(questionId: number) {
  return apiRequest<{ deleted_id: number }>(`/api/admin/questions/${questionId}`, {
    method: "DELETE",
  });
}

export function submitPracticeAnswer(payload: { question_id: number; selected_answer: string }) {
  return apiRequest<PracticeAnswerResult>("/api/practice/answers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getWrongPracticeQuestions(filters?: {
  category_1?: string;
  category_2?: string;
  mastered?: boolean;
  limit?: number;
  offset?: number;
  history_limit?: number;
}) {
  const params = new URLSearchParams();
  if (filters?.category_1) params.set("category_1", filters.category_1);
  if (filters?.category_2) params.set("category_2", filters.category_2);
  if (filters?.mastered !== undefined) params.set("mastered", String(filters.mastered));
  const limit = Number.isFinite(filters?.limit)
    ? Math.min(100, Math.max(1, Math.trunc(filters?.limit ?? 50)))
    : 50;
  const offset = Number.isFinite(filters?.offset)
    ? Math.max(0, Math.trunc(filters?.offset ?? 0))
    : 0;
  const historyLimit = Number.isFinite(filters?.history_limit)
    ? Math.min(100, Math.max(1, Math.trunc(filters?.history_limit ?? 20)))
    : 20;
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  params.set("history_limit", String(historyLimit));
  const query = `?${params.toString()}`;
  return apiRequest<PracticeWrongQuestion[]>(`/api/practice/wrong-questions${query}`);
}
