import { apiRequest } from "@/api/client";
import type {
  ExamCandidateRow,
  ExamRosterPayload,
  InvitationScheduleResult,
  InvitationStatusRead,
} from "@/types/exam";

export function getExamRoster(examId: string) {
  return apiRequest<ExamCandidateRow[]>(`/api/admin/exams/${examId}/candidates`);
}

export function getExamInvitationStatus(examId: string) {
  return apiRequest<InvitationStatusRead>(`/api/admin/exams/${examId}/invitations`);
}

export const getExamInvitations = getExamInvitationStatus;

export function addExamRosterRow(examId: string, payload: ExamRosterPayload) {
  return apiRequest<ExamCandidateRow>(`/api/admin/exams/${examId}/candidates`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateExamRosterRow(
  examId: string,
  candidateId: number,
  payload: Partial<ExamRosterPayload>,
) {
  return apiRequest<ExamCandidateRow>(`/api/admin/exams/${examId}/candidates/${candidateId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function removeExamRosterRow(examId: string, candidateId: number) {
  return apiRequest<{ removed_count: number }>(
    `/api/admin/exams/${examId}/candidates/${candidateId}`,
    { method: "DELETE" },
  );
}

export function sendExamInvitations(examId: string) {
  return apiRequest<InvitationScheduleResult>(`/api/admin/exams/${examId}/invitations/send`, {
    method: "POST",
  });
}

export function resendFailedExamInvitations(examId: string) {
  return apiRequest<InvitationScheduleResult>(`/api/admin/exams/${examId}/invitations/resend`, {
    method: "POST",
  });
}

// Short aliases keep the module convenient for page-level consumers while the
// explicit names make it clear that resend never targets successful deliveries.
export const sendInvitations = sendExamInvitations;
export const resendFailedInvitations = resendFailedExamInvitations;
