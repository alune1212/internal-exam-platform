import { describe, it, expect, beforeEach } from "vitest";
import { getAdminToken, setAdminToken, clearAdminToken } from "./adminSession";

// Node.js v26 has an experimental localStorage that conflicts with jsdom.
// Create an in-memory mock and install it on window before tests run.
function createMockStorage() {
  const store = new Map<string, string>();
  return {
    storage: {
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
    } satisfies Storage,
    store,
  };
}

const local = createMockStorage();
const session = createMockStorage();

Object.defineProperty(window, "localStorage", { value: local.storage });
Object.defineProperty(window, "sessionStorage", { value: session.storage });

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
