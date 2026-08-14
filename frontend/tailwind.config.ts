import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

import { breakpointScreens } from "./src/lib/breakpoints";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    screens: breakpointScreens,
    extend: {
      colors: {
        canvas: "var(--canvas)",
        "canvas-warm": "var(--canvas-warm)",
        "surface-card": "var(--surface-card)",
        "surface-elev": "var(--surface-elev)",
        background: "var(--canvas)",
        foreground: "var(--ink)",
        card: "var(--canvas)",
        "card-foreground": "var(--ink)",
        primary: "var(--ink)",
        "primary-foreground": "var(--canvas)",
        secondary: "var(--surface-card)",
        "secondary-foreground": "var(--ink)",
        destructive: "var(--error)",
        "destructive-foreground": "var(--canvas)",
        accent: "var(--surface-card)",
        "accent-foreground": "var(--ink)",
        border: "var(--hairline)",
        input: "var(--hairline)",
        ring: "var(--ink)",
        "muted-foreground": "var(--muted)",
        ink: {
          DEFAULT: "var(--ink)",
          soft: "var(--ink-soft)",
        },
        body: "var(--body)",
        muted: "var(--muted)",
        hairline: {
          DEFAULT: "var(--hairline)",
          soft: "var(--hairline-soft)",
        },
        footer: {
          DEFAULT: "var(--footer)",
          soft: "var(--footer-soft)",
        },
        success: "var(--success)",
        warning: "var(--warning)",
        error: "var(--error)",
        "success-on-dark": "var(--success-on-dark)",
        "error-on-dark": "var(--error-on-dark)",
        "ink-red": "var(--ink-red)",
        "ink-blue": "var(--ink-blue)",
        overlay: "var(--overlay)",
      },
      borderRadius: {
        pill: "var(--radius-pill)",
        lg: "var(--radius-lg)",
        md: "var(--radius-md)",
        sm: "var(--radius-sm)",
      },
      fontFamily: {
        display: ["var(--font-display)"],
        body: ["var(--font-body)"],
        mono: ["var(--font-mono)"],
      },
      spacing: {
        "page-inline": "var(--space-page-inline)",
        "page-inline-lg": "var(--space-page-inline-lg)",
        "page-block": "var(--space-page-block)",
        section: "var(--space-section)",
        "section-lg": "var(--space-section-lg)",
        panel: "var(--space-panel)",
        field: "var(--space-field)",
        "field-compact": "var(--space-field-compact)",
        "control-x": "var(--space-control-x)",
        "control-y": "var(--space-control-y)",
        "control-gap": "var(--space-control-gap)",
        inline: "var(--space-inline)",
        stack: "var(--space-stack)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        pop: "var(--shadow-pop)",
        elevate: "var(--shadow-elevate)",
        sticky: "var(--shadow-sticky)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer var(--motion-duration-shimmer) var(--motion-ease-linear) infinite",
      },
      fontSize: {
        "display-2xl": [
          "var(--text-display-2xl)",
          {
            lineHeight: "var(--leading-display-2xl)",
            letterSpacing: "var(--tracking-display-tight)",
          },
        ],
        "display-xl": [
          "var(--text-display-xl)",
          {
            lineHeight: "var(--leading-display-xl)",
            letterSpacing: "var(--tracking-display-tight)",
          },
        ],
        "display-lg": [
          "var(--text-display-lg)",
          {
            lineHeight: "var(--leading-display-lg)",
            letterSpacing: "var(--tracking-display-tight)",
          },
        ],
        "display-md": [
          "var(--text-display-md)",
          { lineHeight: "var(--leading-display-md)", letterSpacing: "var(--tracking-display)" },
        ],
        "display-sm": [
          "var(--text-display-sm)",
          { lineHeight: "var(--leading-display-sm)", letterSpacing: "var(--tracking-display)" },
        ],
        "body-lg": ["var(--text-body-lg)", { lineHeight: "var(--leading-body-lg)" }],
        body: ["var(--text-body)", { lineHeight: "var(--leading-body)" }],
        "body-sm": ["var(--text-body-sm)", { lineHeight: "var(--leading-body-sm)" }],
        caption: [
          "var(--text-caption)",
          {
            lineHeight: "var(--leading-caption)",
            letterSpacing: "var(--tracking-caption)",
          },
        ],
      },
      letterSpacing: {
        "display-tight": "var(--tracking-display-tight)",
        display: "var(--tracking-display)",
        caption: "var(--tracking-caption)",
      },
      transitionDuration: {
        DEFAULT: "var(--motion-duration-fast)",
        instant: "var(--motion-duration-instant)",
        fast: "var(--motion-duration-fast)",
        normal: "var(--motion-duration-normal)",
        slow: "var(--motion-duration-slow)",
        shimmer: "var(--motion-duration-shimmer)",
        pulse: "var(--motion-duration-pulse)",
      },
      transitionTimingFunction: {
        DEFAULT: "var(--motion-ease-standard)",
        linear: "var(--motion-ease-linear)",
        standard: "var(--motion-ease-standard)",
      },
      zIndex: {
        background: "var(--z-background)",
        content: "var(--z-content)",
        sticky: "var(--z-sticky)",
        overlay: "var(--z-overlay)",
        modal: "var(--z-modal)",
        toast: "var(--z-toast)",
      },
      ringWidth: {
        DEFAULT: "var(--focus-ring-width)",
      },
      ringOffsetWidth: {
        DEFAULT: "var(--focus-ring-offset)",
      },
    },
  },
  plugins: [animate],
} satisfies Config;
