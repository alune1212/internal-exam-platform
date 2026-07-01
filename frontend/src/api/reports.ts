import { apiRequest, resolveApiUrl } from "@/api/client";
import { getAdminToken } from "@/lib/adminSession";
import type {
  AbsentCandidateRow,
  QuestionAccuracyRow,
  ScoreReportRow,
  WrongQuestionRow,
} from "@/types/report";

function withExamFilter(path: string, examId?: string | null) {
  if (!examId) {
    return path;
  }
  const params = new URLSearchParams({ exam_id: examId });
  return `${path}?${params.toString()}`;
}

export function getScoreReport(examId?: string | null) {
  return apiRequest<ScoreReportRow[]>(withExamFilter("/api/admin/reports/scores", examId));
}

export function getQuestionAccuracy(examId?: string | null) {
  return apiRequest<QuestionAccuracyRow[]>(
    withExamFilter("/api/admin/reports/question-accuracy", examId),
  );
}

export function getWrongQuestions(examId?: string | null) {
  return apiRequest<WrongQuestionRow[]>(
    withExamFilter("/api/admin/reports/wrong-questions", examId),
  );
}

export type AttendanceStatus = "not_started" | "in_progress" | "submitted";

export function getAbsentCandidates(
  status: AttendanceStatus = "not_started",
  examId?: string | null,
) {
  const params = new URLSearchParams({ status });
  if (examId) {
    params.set("exam_id", examId);
  }
  return apiRequest<AbsentCandidateRow[]>(`/api/admin/reports/absent-candidates?${params}`);
}

export async function downloadReportExport(examId?: string | null): Promise<void> {
  const response = await fetch(resolveApiUrl(withExamFilter("/api/admin/reports/export", examId)), {
    headers: { "X-Admin-Token": getAdminToken() ?? "" },
  });
  if (!response.ok) throw new Error("报表导出失败");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "考试报表.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}
