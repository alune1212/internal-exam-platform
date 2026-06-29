import { describe, it, expect, beforeEach } from "vitest";
import { getAdminToken, setAdminToken, clearAdminToken } from "./adminSession";
import { installMockStorage } from "@/test/mockStorage";

installMockStorage();

describe("adminSession", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("初始状态返回 null", () => {
    expect(getAdminToken()).toBeNull();
  });

  it("set 后 get 返回相同值", () => {
    setAdminToken("my-password");
    expect(getAdminToken()).toBe("my-password");
    expect(window.sessionStorage.getItem("internal-exam-admin-token")).toBe("my-password");
  });

  it("clear 后 get 返回 null", () => {
    setAdminToken("my-password");
    window.localStorage.setItem("internal-exam-admin-token", "legacy");
    clearAdminToken();
    expect(getAdminToken()).toBeNull();
    expect(window.localStorage.getItem("internal-exam-admin-token")).toBeNull();
  });

  it("覆盖写入", () => {
    setAdminToken("first");
    setAdminToken("second");
    expect(getAdminToken()).toBe("second");
  });
});
