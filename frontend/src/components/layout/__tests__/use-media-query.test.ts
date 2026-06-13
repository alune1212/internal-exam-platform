import { act, renderHook } from "@testing-library/react";

import { useMediaQuery } from "@/lib/use-media-query";

describe("useMediaQuery", () => {
  let listeners: Array<(event: MediaQueryListEvent) => void>;
  let matchesValue: boolean;

  beforeEach(() => {
    listeners = [];
    matchesValue = false;
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: (query: string) => ({
        get matches() {
          return matchesValue;
        },
        media: query,
        onchange: null,
        addEventListener: (_event: string, cb: (event: MediaQueryListEvent) => void) => {
          listeners.push(cb);
        },
        removeEventListener: (_event: string, cb: (event: MediaQueryListEvent) => void) => {
          listeners = listeners.filter((listener) => listener !== cb);
        },
        dispatchEvent: () => false,
      }),
    });
  });

  it("returns the initial matches value from matchMedia", () => {
    matchesValue = true;
    const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
    expect(result.current).toBe(true);
  });

  it("returns false initially when matchMedia reports no match", () => {
    matchesValue = false;
    const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
    expect(result.current).toBe(false);
  });

  it("updates when matchMedia emits a change event", () => {
    matchesValue = false;
    const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
    expect(result.current).toBe(false);

    act(() => {
      matchesValue = true;
      for (const listener of listeners) {
        listener({ matches: true, media: "(min-width: 1024px)" } as MediaQueryListEvent);
      }
    });

    expect(result.current).toBe(true);
  });

  it("removes the listener on unmount", () => {
    const { unmount } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
    expect(listeners).toHaveLength(1);
    unmount();
    expect(listeners).toHaveLength(0);
  });

  it("returns false when matchMedia is unavailable", () => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: undefined,
    });

    const { result } = renderHook(() => useMediaQuery("(min-width: 1024px)"));
    expect(result.current).toBe(false);
  });
});
