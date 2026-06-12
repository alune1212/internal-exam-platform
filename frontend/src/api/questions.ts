import { apiRequest } from "@/api/client";
import type { PracticeAnswerResult, Question } from "@/types/question";

export function getPracticeQuestions() {
  return apiRequest<Question[]>("/api/practice/questions");
}

export function getAdminQuestions() {
  return apiRequest<Question[]>("/api/admin/questions");
}

export function submitPracticeAnswer(payload: { candidate_id: number; question_id: number; selected_answer: string }) {
  return apiRequest<PracticeAnswerResult>("/api/practice/answers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
