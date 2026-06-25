import { beforeEach, describe, expect, it } from "vitest";

import {
  clearCurrentCandidate,
  getCurrentCandidate,
  setCurrentCandidate,
} from "./candidateSession";
import type { Candidate } from "@/types/candidate";

const localStore = new Map<string, string>();
const sessionStore = new Map<string, string>();

function makeStorage(store: Map<string, string>): Storage {
  return {
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
}

Object.defineProperty(window, "localStorage", { value: makeStorage(localStore) });
Object.defineProperty(window, "sessionStorage", { value: makeStorage(sessionStore) });

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
