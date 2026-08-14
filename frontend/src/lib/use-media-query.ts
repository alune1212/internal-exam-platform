import { useEffect, useState } from "react";

import { breakpointQueries, type BreakpointName, minWidthQuery } from "@/lib/breakpoints";

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }

    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }

    const mediaQueryList = window.matchMedia(query);
    const handleChange = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    setMatches(mediaQueryList.matches);
    mediaQueryList.addEventListener("change", handleChange);

    return () => {
      mediaQueryList.removeEventListener("change", handleChange);
    };
  }, [query]);

  return matches;
}

export const MD = {
  md: breakpointQueries.md,
  lg: breakpointQueries.lg,
} as const;

/**
 * Build a media-query from the shared structural breakpoint map. Keeping this
 * helper next to the hook makes it harder for runtime consumers to drift from
 * Tailwind's screen thresholds.
 */
export function useBreakpoint(name: BreakpointName): boolean {
  return useMediaQuery(minWidthQuery(name));
}
