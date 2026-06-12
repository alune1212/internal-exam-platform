import { apiRequest } from "@/api/client";
import type { ExamStartResponse } from "@/types/attempt";
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

export function startExam(examId: string, candidateId: number) {
  return apiRequest<ExamStartResponse>(`/api/exams/${examId}/start`, {
    method: "POST",
    body: JSON.stringify({ candidate_id: candidateId }),
  });
}
