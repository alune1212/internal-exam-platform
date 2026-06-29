import { beforeEach, describe, expect, it } from "vitest";

import {
  clearCurrentCandidate,
  getCurrentCandidate,
  setCurrentCandidate,
} from "./candidateSession";
import type { Candidate } from "@/types/candidate";
import { installMockStorage } from "@/test/mockStorage";

installMockStorage();

const candidate: Candidate = {
  id: 7,
  token: "candidate-token",
  name: "张三",
  employee_no: "E007",
  department: "技术部",
  status: "active",
  should_attend: true,
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

  it("migrates and clears the legacy localStorage candidate", () => {
    window.localStorage.setItem("internal-exam-candidate", JSON.stringify(candidate));

    expect(getCurrentCandidate()).toEqual(candidate);
    expect(window.localStorage.getItem("internal-exam-candidate")).toBeNull();
    expect(window.sessionStorage.getItem("internal-exam-candidate")).toContain("candidate-token");

    clearCurrentCandidate();

    expect(getCurrentCandidate()).toBeNull();
    expect(window.sessionStorage.getItem("internal-exam-candidate")).toBeNull();
  });
});
