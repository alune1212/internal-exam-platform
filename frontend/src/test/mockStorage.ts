// In-memory Storage mock for tests.
//
// Node.js v26 has an experimental localStorage that conflicts with jsdom.
// Install this on `window.localStorage` and `window.sessionStorage` before
// running session-related tests, e.g. in `adminSession.test.ts` and
// `candidateSession.test.ts`. See CLAUDE.md for context.

export function createMockStorage(): Storage {
  const store = new Map<string, string>();
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

export function installMockStorage(): void {
  Object.defineProperty(window, "localStorage", {
    value: createMockStorage(),
    configurable: true,
    writable: true,
  });
  Object.defineProperty(window, "sessionStorage", {
    value: createMockStorage(),
    configurable: true,
    writable: true,
  });
}
