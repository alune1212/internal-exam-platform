import { apiRequest } from "@/api/client";
import type { Question } from "@/types/question";

export function getPracticeQuestions() {
  return apiRequest<Question[]>("/api/practice/questions");
}

export function getAdminQuestions() {
  return apiRequest<Question[]>("/api/admin/questions");
}
