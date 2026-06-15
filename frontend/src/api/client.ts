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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function resolveAuthHeaders(path: string): Record<string, string> {
  if (path.includes("/api/admin/")) {
    const token = getAdminToken();
    return token ? { "X-Admin-Token": token } : {};
  }
  const candidate = getCurrentCandidate();
  if (candidate) {
    return { "X-Candidate-Id": String(candidate.id) };
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
    clearAdminToken();
    window.location.href = "/admin/login";
  } else {
    clearCurrentCandidate();
    window.location.href = "/login";
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...resolveAuthHeaders(path),
      ...init?.headers,
    },
    ...init,
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

export async function uploadRequest<T>(path: string, file: File): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    body: formData,
    headers: {
      ...resolveAuthHeaders(path),
    },
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
