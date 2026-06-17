import { uploadRequest } from "@/api/client";
import type { QuestionImportResult } from "@/types/imports";

export function importQuestions(file: File) {
  return uploadRequest<QuestionImportResult>("/api/admin/questions/import", file);
}

export function importCandidates(examId: string, file: File) {
  return uploadRequest<QuestionImportResult>(`/api/admin/exams/${examId}/candidates/import`, file);
}

export async function downloadImportTemplate(type: "questions" | "candidates"): Promise<void> {
  const { getAdminToken } = await import("@/lib/adminSession");
  const response = await fetch(`/api/admin/imports/templates/${type}`, {
    headers: { "X-Admin-Token": getAdminToken() ?? "" },
  });
  if (!response.ok) throw new Error("下载失败");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = type === "questions" ? "题库导入模板.xlsx" : "应考人员模板.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadImportFailureReport(batchId: number): Promise<void> {
  const { getAdminToken } = await import("@/lib/adminSession");
  const response = await fetch(`/api/admin/imports/${batchId}/failure-report`, {
    headers: { "X-Admin-Token": getAdminToken() ?? "" },
  });
  if (!response.ok) throw new Error("下载失败");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "导入失败明细.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}
