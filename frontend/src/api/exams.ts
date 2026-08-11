import { apiRequest, uploadRequest } from "@/api/client";
import type { ExamStartResponse } from "@/types/attempt";
import type {
  AttemptIncident,
  BulkRetakeApply,
  BulkRetakePreview,
  Exam,
  ExamCandidateRow,
  PublicationReadiness,
  ResultDetailsRelease,
} from "@/types/exam";
import type { QuestionImportResult } from "@/types/imports";

export function getActiveExams() {
  return apiRequest<Exam[]>("/api/exams/active");
}

export function getAdminExams() {
  return apiRequest<Exam[]>("/api/admin/exams");
}

export function createAdminExam() {
  return apiRequest<Exam>("/api/admin/exams", {
    method: "POST",
    body: JSON.stringify({
      title: "新考试",
      description: null,
      duration_minutes: 60,
      question_rule: {
        question_count: 50,
        total_score: 100,
        pass_score: 60,
        mode: "fixed_paper",
        type_counts: { single: 30, multiple: 10, judge: 10 },
      },
      status: "draft",
      show_answer_after_submit: true,
    }),
  });
}

export type ExamUpdatePayload = {
  title?: string;
  duration_minutes?: number;
  question_rule?: Record<string, unknown>;
  status?: string;
  available_from?: string | null;
  available_until?: string | null;
};

export function updateAdminExam(examId: string, payload: ExamUpdatePayload) {
  return apiRequest<Exam>(`/api/admin/exams/${examId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function getPublicationReadiness(examId: string) {
  return apiRequest<PublicationReadiness>(`/api/admin/exams/${examId}/publication-readiness`);
}

export function publishAdminExam(examId: string, confirmationTitle: string) {
  return apiRequest<Exam>(`/api/admin/exams/${examId}/publish`, {
    method: "POST",
    body: JSON.stringify({ confirmation_title: confirmationTitle }),
  });
}

export function releaseResultDetails(examId: string, confirmationTitle: string) {
  return apiRequest<ResultDetailsRelease>(`/api/admin/exams/${examId}/result-details/release`, {
    method: "POST",
    body: JSON.stringify({ confirmation_title: confirmationTitle }),
  });
}

export function getExamIncidents(examId: string) {
  return apiRequest<AttemptIncident[]>(`/api/admin/exams/${examId}/incidents`);
}

export function voidExamAttempt(examId: string, attemptId: number, reason: string) {
  return apiRequest<AttemptIncident>(`/api/admin/exams/${examId}/attempts/${attemptId}/void`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function previewBulkRetake(examId: string, candidateIds: number[], voidExisting: boolean) {
  return apiRequest<BulkRetakePreview>(`/api/admin/exams/${examId}/retakes/preview`, {
    method: "POST",
    body: JSON.stringify({ candidate_ids: candidateIds, void_existing: voidExisting }),
  });
}

export function applyBulkRetake(
  examId: string,
  payload: {
    candidateIds: number[];
    voidExisting: boolean;
    confirmationTitle: string;
    previewFingerprint: string;
    reason: string;
  },
) {
  return apiRequest<BulkRetakeApply>(`/api/admin/exams/${examId}/retakes/apply`, {
    method: "POST",
    body: JSON.stringify({
      candidate_ids: payload.candidateIds,
      void_existing: payload.voidExisting,
      confirmation_title: payload.confirmationTitle,
      preview_fingerprint: payload.previewFingerprint,
      reason: payload.reason,
    }),
  });
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
