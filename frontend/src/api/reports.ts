import { apiRequest } from "@/api/client";
import { getAdminToken } from "@/lib/adminSession";
import type {
  AbsentCandidateRow,
  QuestionAccuracyRow,
  ScoreReportRow,
  WrongQuestionRow,
} from "@/types/report";

export function getScoreReport() {
  return apiRequest<ScoreReportRow[]>("/api/admin/reports/scores");
}

export function getQuestionAccuracy() {
  return apiRequest<QuestionAccuracyRow[]>("/api/admin/reports/question-accuracy");
}

export function getWrongQuestions() {
  return apiRequest<WrongQuestionRow[]>("/api/admin/reports/wrong-questions");
}

export function getAbsentCandidates() {
  return apiRequest<AbsentCandidateRow[]>("/api/admin/reports/absent-candidates");
}

export async function downloadReportExport(): Promise<void> {
  const response = await fetch("/api/admin/reports/export", {
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
