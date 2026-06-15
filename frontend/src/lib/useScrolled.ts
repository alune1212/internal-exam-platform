import { useEffect, useState } from "react";

/**
 * Returns `true` once the window has scrolled past `threshold` pixels.
 * Used to toggle a `data-scrolled` attribute on sticky headers so they
 * can pick up a hairline shadow only after the user has begun scrolling.
 */
export function useScrolled(threshold = 8): boolean {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const onScroll = () => {
      setScrolled(window.scrollY > threshold);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [threshold]);

  return scrolled;
}
