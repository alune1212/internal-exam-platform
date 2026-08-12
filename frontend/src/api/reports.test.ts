import { beforeEach, describe, expect, it, vi } from "vitest";

describe("downloadReportExport", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    sessionStorage.clear();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:report"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  it("uses API base URL, exam filter, and admin token for report downloads", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.example.test");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve(new Blob(["mock report"])),
      }),
    );
    const { setAdminToken } = await import("@/lib/adminSession");
    const { downloadReportExport } = await import("@/api/reports");

    setAdminToken("admin-pass");
    await downloadReportExport("7");

    expect(fetch).toHaveBeenCalledWith(
      "http://api.example.test/api/admin/reports/export?exam_id=7",
      expect.objectContaining({
        headers: { "X-Admin-Token": "admin-pass" },
      }),
    );
    expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:report");
  });

  it("throws when report download response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
    const { downloadReportExport } = await import("@/api/reports");

    await expect(downloadReportExport()).rejects.toThrow("报表导出失败");
  });
});

describe("getRanking", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    sessionStorage.clear();
  });

  it("requests the selected exam ranking with the admin token", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://api.example.test");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ success: true, data: [], message: "" }),
      }),
    );
    const { setAdminToken } = await import("@/lib/adminSession");
    const { getRanking } = await import("@/api/reports");

    setAdminToken("admin-pass");
    await getRanking("7");

    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.example.test/api/admin/reports/rankings?exam_id=7");
    expect((init.headers as Headers).get("X-Admin-Token")).toBe("admin-pass");
  });
});
