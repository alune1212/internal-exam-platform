import { uploadRequest } from "@/api/client";

export type ImportFailure = {
  row_number: number;
  reason: string;
};

export type QuestionImportResult = {
  success_count: number;
  failed_count: number;
  failures: ImportFailure[];
};

export function importQuestions(file: File) {
  return uploadRequest<QuestionImportResult>("/api/admin/questions/import", file);
}

export function importCandidates(examId: string, file: File) {
  return uploadRequest<{ exam_id: number; success_count: number; failed_count: number }>(
    `/api/admin/exams/${examId}/candidates/import`,
    file,
  );
}
