/**
 * Data-derived avatar/chip accents only.
 *
 * This is the one intentional visual-color exception: values are selected
 * from a stable identity seed and are not a general UI, status, or surface
 * palette. Product surfaces and states must use the CSS tokens in index.css.
 */
export const PASTEL_COLORS = ["#fef3c7", "#dbeafe", "#dcfce7", "#fce7f3", "#e0e7ff"] as const;

export type PastelColor = (typeof PASTEL_COLORS)[number];

/**
 * Deterministically pick a pastel color from a string seed.
 * Same input returns the same output across renders and tests.
 */
export function pickPastel(seed: string): PastelColor {
  if (!seed) return PASTEL_COLORS[0];

  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }

  return PASTEL_COLORS[hash % PASTEL_COLORS.length];
}
