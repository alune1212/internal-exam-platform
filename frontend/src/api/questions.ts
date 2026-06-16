import { apiRequest } from "@/api/client";
import type { PracticeAnswerResult, Question, QuestionPayload } from "@/types/question";

export function getPracticeQuestions() {
  return apiRequest<Question[]>("/api/practice/questions");
}

export function getAdminQuestions() {
  return apiRequest<Question[]>("/api/admin/questions");
}

export function createAdminQuestion(payload: QuestionPayload) {
  return apiRequest<Question>("/api/admin/questions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAdminQuestion(questionId: number, payload: Partial<QuestionPayload>) {
  return apiRequest<Question>(`/api/admin/questions/${questionId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteAdminQuestion(questionId: number) {
  return apiRequest<{ deleted_id: number }>(`/api/admin/questions/${questionId}`, {
    method: "DELETE",
  });
}

export function submitPracticeAnswer(payload: {
  candidate_id: number;
  question_id: number;
  selected_answer: string;
}) {
  return apiRequest<PracticeAnswerResult>("/api/practice/answers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
