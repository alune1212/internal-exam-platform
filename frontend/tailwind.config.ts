import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
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
      boxShadow: {
        card: "var(--shadow-card)",
        pop: "var(--shadow-pop)",
        elevate: "var(--shadow-elevate)",
      },
      keyframes: {
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        shimmer: "shimmer 1500ms linear infinite",
      },
      fontSize: {
        "display-2xl": ["64px", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        "display-xl": ["48px", { lineHeight: "1.08", letterSpacing: "-0.02em" }],
        "display-lg": ["36px", { lineHeight: "1.12", letterSpacing: "-0.02em" }],
        "display-md": ["26px", { lineHeight: "1.22", letterSpacing: "-0.01em" }],
        "display-sm": ["20px", { lineHeight: "1.3", letterSpacing: "-0.01em" }],
        "body-lg": ["17px", { lineHeight: "1.7" }],
        body: ["15px", { lineHeight: "1.7" }],
        "body-sm": ["13px", { lineHeight: "1.6" }],
        caption: [
          "11px",
          {
            lineHeight: "1.4",
            letterSpacing: "0.16em",
          },
        ],
      },
    },
  },
  plugins: [animate],
} satisfies Config;
