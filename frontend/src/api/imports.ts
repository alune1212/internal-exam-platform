import { uploadRequest } from "@/api/client";
import type { QuestionImportResult } from "@/types/imports";

export function importQuestions(file: File) {
  return uploadRequest<QuestionImportResult>("/api/admin/questions/import", file);
}

export function importCandidates(examId: string, file: File) {
  return uploadRequest<{ exam_id: number; success_count: number; failed_count: number }>(
    `/api/admin/exams/${examId}/candidates/import`,
    file,
  );
}
