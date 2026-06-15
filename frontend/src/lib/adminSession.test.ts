import { describe, it, expect, beforeEach } from "vitest";
import { getAdminToken, setAdminToken, clearAdminToken } from "./adminSession";

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

describe("adminSession", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("初始状态返回 null", () => {
    expect(getAdminToken()).toBeNull();
  });

  it("set 后 get 返回相同值", () => {
    setAdminToken("my-password");
    expect(getAdminToken()).toBe("my-password");
  });

  it("clear 后 get 返回 null", () => {
    setAdminToken("my-password");
    clearAdminToken();
    expect(getAdminToken()).toBeNull();
  });

  it("覆盖写入", () => {
    setAdminToken("first");
    setAdminToken("second");
    expect(getAdminToken()).toBe("second");
  });
});
