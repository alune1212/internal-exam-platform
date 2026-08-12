import { beforeEach, describe, expect, it } from "vitest";

import {
  clearCurrentCandidate,
  getRegistrationFlow,
  getSafeReturnTo,
  getCurrentCandidate,
  maskEmail,
  setRegistrationFlow,
  setCurrentCandidate,
} from "./candidateSession";
import type { Candidate } from "@/types/candidate";
import { installMockStorage } from "@/test/mockStorage";

installMockStorage();

const candidate: Candidate = {
  id: 7,
  token: "candidate-token",
  token_expires_at: "2099-01-01T00:00:00.000Z",
  email: "zhangsan@example.com",
  display_name: "张三",
  status: "active",
};

describe("candidateSession", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("stores the current candidate in sessionStorage", () => {
    setCurrentCandidate(candidate);

    expect(getCurrentCandidate()).toEqual(candidate);
    expect(window.sessionStorage.getItem("internal-exam-candidate")).toContain("candidate-token");
    expect(window.localStorage.getItem("internal-exam-candidate")).toBeNull();
  });

  it("does not restore a candidate token from localStorage", () => {
    window.localStorage.setItem("internal-exam-candidate", JSON.stringify(candidate));

    expect(getCurrentCandidate()).toBeNull();
    expect(window.localStorage.getItem("internal-exam-candidate")).toContain("candidate-token");

    clearCurrentCandidate();

    expect(getCurrentCandidate()).toBeNull();
    expect(window.sessionStorage.getItem("internal-exam-candidate")).toBeNull();
  });

  it("clears an expired session before it can be used", () => {
    window.sessionStorage.setItem(
      "internal-exam-candidate",
      JSON.stringify({ ...candidate, token_expires_at: "2020-01-01T00:00:00.000Z" }),
    );

    expect(getCurrentCandidate()).toBeNull();
    expect(window.sessionStorage.getItem("internal-exam-candidate")).toBeNull();
  });

  it("keeps return targets same-origin and preserves an in-app query", () => {
    expect(getSafeReturnTo("/exams/7/start?from=email#rules")).toBe(
      "/exams/7/start?from=email#rules",
    );
    expect(getSafeReturnTo("https://evil.example/phish")).toBe("/exams");
    expect(getSafeReturnTo("//evil.example/phish")).toBe("/exams");
    expect(getSafeReturnTo("/\\\\evil.example/phish")).toBe("/exams");
  });

  it("stores registration credentials only in sessionStorage", () => {
    setRegistrationFlow({
      registration_credential: "opaque-credential",
      email: "new@example.com",
      suggested_display_name: "新用户",
      returnTo: "/exams/7/start",
      expires_at: "2099-01-01T00:00:00.000Z",
    });

    expect(getRegistrationFlow()).toMatchObject({
      registration_credential: "opaque-credential",
      email: "new@example.com",
      returnTo: "/exams/7/start",
    });
    expect(window.localStorage.getItem("internal-exam-registration-flow")).toBeNull();
    expect(maskEmail("zhangsan@example.com")).toBe("z****n@example.com");
  });
});
