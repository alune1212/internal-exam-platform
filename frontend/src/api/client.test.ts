import { describe, it, expect, beforeEach, vi } from "vitest";
import { apiRequest, ApiError } from "./client";
import { setAdminToken, clearAdminToken } from "@/lib/adminSession";
import { setCurrentCandidate, clearCurrentCandidate } from "@/lib/candidateSession";
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
  name: "张三",
  employee_no: "E001",
  department: "技术部",
  status: "active",
  should_attend: true,
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
    vi.restoreAllMocks();
  });

  it("admin 路径自动带 X-Admin-Token", async () => {
    setAdminToken("admin-pass");
    mockFetchJson([]);
    await apiRequest("/api/admin/exams");
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.headers).toMatchObject({ "X-Admin-Token": "admin-pass" });
  });

  it("admin 路径无 token 时不带 header", async () => {
    clearAdminToken();
    mockFetchJson([]);
    await apiRequest("/api/admin/exams");
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.headers).not.toHaveProperty("X-Admin-Token");
  });

  it("候选人路径自动带 X-Candidate-Id", async () => {
    setCurrentCandidate(mockCandidate);
    mockFetchJson({ attempt_id: 1 });
    await apiRequest("/api/exams/1/start", { method: "POST" });
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.headers).toMatchObject({ "X-Candidate-Id": "42" });
  });

  it("公开路径无候选人时不带 candidate header", async () => {
    clearCurrentCandidate();
    mockFetchJson([]);
    await apiRequest("/api/exams/active");
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(init?.headers).not.toHaveProperty("X-Candidate-Id");
  });

  it("401 admin 请求清 token", async () => {
    setAdminToken("old-pass");
    mockFetchJson(null, 401);
    await expect(apiRequest("/api/admin/exams")).rejects.toBeInstanceOf(ApiError);
    expect(localStorage.getItem("internal-exam-admin-token")).toBeNull();
  });
});
