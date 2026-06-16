import { apiRequest, uploadRequest } from "@/api/client";
import type { ExamStartResponse } from "@/types/attempt";
import type { Exam, ExamCandidateRow, RankingRow } from "@/types/exam";
import type { QuestionImportResult } from "@/types/imports";

export function getActiveExams() {
  return apiRequest<Exam[]>("/api/exams/active");
}

export function getAdminExams() {
  return apiRequest<Exam[]>("/api/admin/exams");
}

export type ExamUpdatePayload = {
  title?: string;
  duration_minutes?: number;
  question_rule?: Record<string, unknown>;
  status?: string;
};

export function updateAdminExam(examId: string, payload: ExamUpdatePayload) {
  return apiRequest<Exam>(`/api/admin/exams/${examId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function getExamRanking(examId: string) {
  return apiRequest<RankingRow[]>(`/api/exams/${examId}/ranking`);
}

export function startExam(examId: string) {
  return apiRequest<ExamStartResponse>(`/api/exams/${examId}/start`, {
    method: "POST",
  });
}

export function getExamCandidates(examId: string) {
  return apiRequest<ExamCandidateRow[]>(`/api/admin/exams/${examId}/candidates`);
}

export function importExamCandidates(examId: string, file: File) {
  return uploadRequest<QuestionImportResult>(`/api/admin/exams/${examId}/candidates/import`, file);
}

export function removeExamCandidate(examId: string, candidateId: number) {
  return apiRequest<{ removed_count: number }>(
    `/api/admin/exams/${examId}/candidates/${candidateId}`,
    { method: "DELETE" },
  );
}

export function createRetakeGrant(examId: string, candidateId: number) {
  return apiRequest<ExamCandidateRow>(
    `/api/admin/exams/${examId}/candidates/${candidateId}/retake-grants`,
    { method: "POST" },
  );
}
