import type { ReactNode } from "react";

/**
 * Decide whether a ReactNode carries visible content worth rendering.
 * Used by quiet editorial primitives (ContextLabel, ChapterNumber, PageHeader)
 * to suppress themselves when the caller passes an empty/whitespace string,
 * null, a boolean, or an array of such values.
 */
export function hasMeaningfulContent(value: ReactNode): boolean {
  if (value === null || value === undefined || typeof value === "boolean") return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return value.some(hasMeaningfulContent);
  return true;
}
