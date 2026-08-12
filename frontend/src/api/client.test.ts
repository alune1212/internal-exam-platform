import { describe, it, expect, beforeEach, vi } from "vitest";
import { apiRequest, ApiError } from "./client";
import { setAdminToken, clearAdminToken } from "@/lib/adminSession";
import { setCurrentCandidate, clearCurrentCandidate } from "@/lib/candidateSession";
import { setAttemptSession } from "@/lib/attemptSession";
import { writeAttemptDraft } from "@/lib/attemptDraft";
import type { Candidate } from "@/types/candidate";

// Node.js v26 has an experimental localStorage that conflicts with jsdom.
// Create an in-memory mock and install it on window before tests run.
const store = new Map<string, string>();
const mockStorage: Storage = {
  getItem: (key: string) => store.get(key) ?? null,
  setItem: (key: string, value: string) => {
    store.set(key, value);
  },
  removeItem: (key: string) => {
    store.delete(key);
  },
  clear: () => {
    store.clear();
  },
  get length() {
    return store.size;
  },
  key: (index: number) => [...store.keys()][index] ?? null,
};

Object.defineProperty(window, "localStorage", { value: mockStorage });

const mockCandidate: Candidate = {
  id: 42,
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "zhangsan@example.com",
  display_name: "张三",
  status: "active",
};

function mockFetchJson(data: unknown, status = 200) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: () =>
        Promise.resolve(
          status >= 200 && status < 300
            ? { success: true, data, message: "ok" }
            : { detail: "error" },
        ),
    }),
  );
}

describe("apiRequest auth headers", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    window.history.replaceState(null, "", "/");
    vi.restoreAllMocks();
  });

  it("admin 路径自动带 X-Admin-Token", async () => {
    setAdminToken("admin-pass");
    mockFetchJson([]);
    await apiRequest("/api/admin/exams");
    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init?.headers as Headers;
    expect(headers.get("X-Admin-Token")).toBe("admin-pass");
  });

  it("admin 路径无 token 时不带 header", async () => {
    clearAdminToken();
    mockFetchJson([]);
    await apiRequest("/api/admin/exams");
    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init?.headers as Headers;
    expect(headers.get("X-Admin-Token")).toBeNull();
  });

  it("候选人路径自动带 X-Candidate-Token", async () => {
    setCurrentCandidate(mockCandidate);
    mockFetchJson({ attempt_id: 1 });
    await apiRequest("/api/exams/1/start", { method: "POST" });
    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init?.headers as Headers;
    expect(headers.get("X-Candidate-Token")).toBe("candidate-token");
    expect(headers.get("X-Candidate-Id")).toBeNull();
  });

  it("调用方 headers 不会覆盖认证 header", async () => {
    setAdminToken("admin-pass");
    mockFetchJson([]);

    await apiRequest("/api/admin/exams", {
      headers: { "X-Admin-Token": "caller-token", "X-Trace-Id": "trace-1" },
    });

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init?.headers as Headers;
    expect(headers.get("X-Admin-Token")).toBe("admin-pass");
    expect(headers.get("X-Trace-Id")).toBe("trace-1");
  });

  it("FormData 请求不强制 JSON Content-Type", async () => {
    setAdminToken("admin-pass");
    mockFetchJson([]);
    const formData = new FormData();
    formData.append("file", new File(["x"], "x.xlsx"));

    await apiRequest("/api/admin/questions/import", {
      method: "POST",
      body: formData,
    });

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init?.headers as Headers;
    expect(headers.get("Content-Type")).toBeNull();
    expect(headers.get("X-Admin-Token")).toBe("admin-pass");
  });

  it("公开路径无候选人时不带 candidate header", async () => {
    clearCurrentCandidate();
    mockFetchJson([]);
    await apiRequest("/api/exams/active");
    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = init?.headers as Headers;
    expect(headers.get("X-Candidate-Token")).toBeNull();
  });

  it("401 admin 请求清 token", async () => {
    setAdminToken("old-pass");
    mockFetchJson(null, 401);
    await expect(apiRequest("/api/admin/exams")).rejects.toBeInstanceOf(ApiError);
    expect(sessionStorage.getItem("internal-exam-admin-token")).toBeNull();
    expect(window.location.pathname).toBe("/admin/login");
  });

  it("401 候选人请求清 token", async () => {
    setCurrentCandidate(mockCandidate);
    const attemptSession = {
      candidateId: mockCandidate.id,
      attemptId: 9,
      credential: "attempt-token",
      generation: 1,
      answerRevision: 0,
    };
    setAttemptSession(attemptSession);
    writeAttemptDraft(attemptSession, { 1: "A" });
    mockFetchJson(null, 401);
    await expect(apiRequest("/api/exams/active")).rejects.toBeInstanceOf(ApiError);
    expect(sessionStorage.getItem("internal-exam-candidate")).toBeNull();
    expect(sessionStorage.getItem("internal-exam-attempt-session:42:9")).toBeNull();
    expect(sessionStorage.getItem("internal-exam-attempt-draft:42:9")).toBeNull();
    expect(window.location.pathname).toBe("/login");
  });
});
