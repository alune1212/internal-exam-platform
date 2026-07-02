import { apiRequest, formRequest, resolveApiUrl } from "@/api/client";
import { getAdminToken } from "@/lib/adminSession";
import type {
  CandidateLearningVideo,
  LearningCompletionStatus,
  LearningProgressPayload,
  LearningReportRow,
  LearningVideo,
  LearningVideoUpdatePayload,
  LearningVideoUploadPayload,
} from "@/types/learning";

export function getLearningVideos() {
  return apiRequest<CandidateLearningVideo[]>("/api/learning/videos");
}

export function getLearningVideo(videoId: string) {
  return apiRequest<CandidateLearningVideo>(`/api/learning/videos/${videoId}`);
}

export function updateLearningProgress(videoId: number, payload: LearningProgressPayload) {
  return apiRequest<CandidateLearningVideo["progress"]>(
    `/api/learning/videos/${videoId}/progress`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function getAdminLearningVideos() {
  return apiRequest<LearningVideo[]>("/api/admin/learning/videos");
}

export function uploadLearningVideo(payload: LearningVideoUploadPayload) {
  const formData = new FormData();
  formData.append("title", payload.title);
  formData.append("duration_seconds", String(payload.duration_seconds));
  if (payload.description) {
    formData.append("description", payload.description);
  }
  formData.append("file", payload.file);
  return formRequest<LearningVideo>("/api/admin/learning/videos", formData);
}

export function updateAdminLearningVideo(videoId: number, payload: LearningVideoUpdatePayload) {
  return apiRequest<LearningVideo>(`/api/admin/learning/videos/${videoId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function publishLearningVideo(videoId: number) {
  return apiRequest<LearningVideo>(`/api/admin/learning/videos/${videoId}/publish`, {
    method: "POST",
  });
}

export function archiveLearningVideo(videoId: number) {
  return apiRequest<LearningVideo>(`/api/admin/learning/videos/${videoId}/archive`, {
    method: "POST",
  });
}

function withLearningReportFilters(
  path: string,
  filters?: { videoId?: string | null; status?: LearningCompletionStatus | "all" | null },
) {
  const params = new URLSearchParams();
  if (filters?.videoId) {
    params.set("video_id", filters.videoId);
  }
  if (filters?.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}

export function getLearningReport(filters?: {
  videoId?: string | null;
  status?: LearningCompletionStatus | "all" | null;
}) {
  return apiRequest<LearningReportRow[]>(
    withLearningReportFilters("/api/admin/learning/reports", filters),
  );
}

export async function downloadLearningReportExport(filters?: {
  videoId?: string | null;
  status?: LearningCompletionStatus | "all" | null;
}): Promise<void> {
  const response = await fetch(
    resolveApiUrl(withLearningReportFilters("/api/admin/learning/reports/export", filters)),
    {
      headers: { "X-Admin-Token": getAdminToken() ?? "" },
    },
  );
  if (!response.ok) throw new Error("视频学习报表导出失败");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "视频学习报表.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}
