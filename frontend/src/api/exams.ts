import { apiRequest } from "@/api/client";
import type { Exam, RankingRow } from "@/types/exam";

export function getActiveExams() {
  return apiRequest<Exam[]>("/api/exams/active");
}

export function getAdminExams() {
  return apiRequest<Exam[]>("/api/admin/exams");
}

export function getExamRanking(examId: string) {
  return apiRequest<RankingRow[]>(`/api/exams/${examId}/ranking`);
}
