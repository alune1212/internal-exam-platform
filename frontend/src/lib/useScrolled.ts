import { useEffect, useRef, useState } from "react";

/**
 * Returns `true` once the window has scrolled past `threshold` pixels.
 * Used to toggle a `data-scrolled` attribute on sticky headers so they
 * can pick up a hairline shadow only after the user has begun scrolling.
 */
export function useScrolled(threshold = 8): boolean {
  const [scrolled, setScrolled] = useState(false);
  const lastScrolledRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const update = () => {
      const next = window.scrollY > threshold;
      // Avoid ~60 setState dispatches per second of continuous scroll when
      // the boolean hasn't actually flipped.
      if (next === lastScrolledRef.current) return;
      lastScrolledRef.current = next;
      setScrolled(next);
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, [threshold]);

  return scrolled;
}
