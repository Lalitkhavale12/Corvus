/** @type {import('tailwindcss').Config} */
// Colour tokens are semantic, not literal: components reference `surface-low`,
// `primary`, `success-ink` and never a raw hex. Retuning the palette means
// editing this file only. Contrast of every text pair is verified against
// WCAG AA on the rendered pages by e2e/audit.mjs.
//
// Direction: neutral warm greys + teal accent. Teal replaces the previous navy
// because it reads as clinical without the "banking dashboard" blue.
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces, light to dark (warm neutral, not slate)
        surface: "#F7F7F6",
        "surface-lowest": "#FFFFFF",
        "surface-low": "#F1F1EF",
        "surface-container": "#E7E7E4",
        "surface-high": "#DCDCD8",
        // Text
        "on-surface": "#17191C",
        "on-surface-variant": "#5A6068",
        outline: "#85888C",
        "outline-variant": "#E3E3DF",
        // Brand
        primary: "#0E7490",
        "primary-container": "#155E75",
        "primary-soft": "#ECFEFF",
        "primary-line": "#A5F3FC",
        "on-primary": "#FFFFFF",
        secondary: "#334155",
        "secondary-container": "#E2E8F0",
        // Status: soft = fill, ink = text on that fill, line = border
        success: "#15803D",
        "success-soft": "#DCFCE7",
        "success-ink": "#166534",
        "success-line": "#BBF7D0",
        warning: "#B45309",
        "warning-soft": "#FEF3C7",
        "warning-ink": "#92400E",
        "warning-line": "#FDE68A",
        danger: "#DC2626",
        "danger-soft": "#FEF2F2",
        "danger-ink": "#B91C1C",
        "danger-line": "#FECACA",
        // Legacy aliases kept so existing classNames keep working
        tertiary: "#DC2626",
        error: "#DC2626",
        "error-container": "#FEF2F2",
        "on-error-container": "#B91C1C",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "6px",
        md: "8px",
        lg: "10px",
        xl: "12px",
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(23 25 28 / 0.04), 0 1px 3px 0 rgb(23 25 28 / 0.06)",
        pop: "0 8px 24px -4px rgb(23 25 28 / 0.12), 0 2px 8px -2px rgb(23 25 28 / 0.08)",
      },
    },
  },
  plugins: [],
};
