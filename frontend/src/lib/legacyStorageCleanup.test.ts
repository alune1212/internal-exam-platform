import { beforeEach, describe, expect, it } from "vitest";

import { clearLegacyProjectStorage } from "@/lib/legacyStorageCleanup";
import { installMockStorage } from "@/test/mockStorage";

installMockStorage();

describe("legacyStorageCleanup", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("removes only known project keys and attempt prefixes", () => {
    window.localStorage.setItem("internal-exam-admin-token", "legacy-admin");
    window.localStorage.setItem("internal-exam-candidate", "legacy-candidate");
    window.localStorage.setItem("internal-exam-registration-flow", "legacy-registration");
    window.localStorage.setItem("internal-exam-attempt-session:7:19", "legacy-session");
    window.localStorage.setItem("internal-exam-attempt-draft:7:19", "legacy-draft");
    window.localStorage.setItem("internal-exam-attempt-session-not-a-key", "keep");
    window.localStorage.setItem("unrelated-app-state", "keep");
    window.sessionStorage.setItem("internal-exam-admin-token", "current-admin");

    clearLegacyProjectStorage();

    expect(window.localStorage.getItem("internal-exam-admin-token")).toBeNull();
    expect(window.localStorage.getItem("internal-exam-candidate")).toBeNull();
    expect(window.localStorage.getItem("internal-exam-registration-flow")).toBeNull();
    expect(window.localStorage.getItem("internal-exam-attempt-session:7:19")).toBeNull();
    expect(window.localStorage.getItem("internal-exam-attempt-draft:7:19")).toBeNull();
    expect(window.localStorage.getItem("internal-exam-attempt-session-not-a-key")).toBe("keep");
    expect(window.localStorage.getItem("unrelated-app-state")).toBe("keep");
    expect(window.sessionStorage.getItem("internal-exam-admin-token")).toBe("current-admin");
  });
});
