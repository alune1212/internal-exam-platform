import { getAdminToken, clearAdminToken } from "@/lib/adminSession";
import { getCurrentCandidate, clearCurrentCandidate } from "@/lib/candidateSession";

export type ApiResponse<T> = {
  success: boolean;
  data: T;
  message: string;
};

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function getErrorMessage(error: unknown, fallback = "操作失败，请稍后重试。"): string {
  if (error instanceof ApiError) return error.detail ?? error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export function resolveApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

function resolveAuthHeaders(path: string): Record<string, string> {
  if (path.includes("/api/admin/")) {
    const token = getAdminToken();
    return token ? { "X-Admin-Token": token } : {};
  }
  const candidate = getCurrentCandidate();
  if (candidate?.token) {
    return { "X-Candidate-Token": candidate.token };
  }
  return {};
}

async function parseError(response: Response): Promise<ApiError> {
  let detail: string | undefined;
  try {
    const body = (await response.json()) as { detail?: unknown; message?: unknown } | null;
    if (body && typeof body.detail === "string") {
      detail = body.detail;
    } else if (body && typeof body.message === "string") {
      detail = body.message;
    }
  } catch {
    // response body was not JSON; fall through to status-only message
  }
  const message = detail ?? `Request failed: ${response.status}`;
  return new ApiError(message, response.status, detail);
}

function handle401(path: string): void {
  if (path.includes("/api/admin/")) {
    clearAdminToken("unauthorized");
    redirectTo("/admin/login");
  } else {
    clearCurrentCandidate("unauthorized");
    redirectTo("/login");
  }
}

function redirectTo(path: string): void {
  window.history.replaceState(null, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const { headers: initHeaders, body: requestBody, ...restInit } = init ?? {};
  const headers = new Headers(initHeaders);
  if (!(requestBody instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  Object.entries(resolveAuthHeaders(path)).forEach(([key, value]) => headers.set(key, value));

  const response = await fetch(resolveApiUrl(path), {
    ...restInit,
    body: requestBody,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      handle401(path);
    }
    throw await parseError(response);
  }

  const responseBody = (await response.json()) as ApiResponse<T>;
  return responseBody.data;
}

export async function uploadRequest<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(resolveApiUrl(path), {
    method: "POST",
    body: formData,
    headers: new Headers(resolveAuthHeaders(path)),
  });
  if (!response.ok) {
    if (response.status === 401) {
      handle401(path);
    }
    throw await parseError(response);
  }
  const body = (await response.json()) as ApiResponse<T>;
  return body.data;
}
