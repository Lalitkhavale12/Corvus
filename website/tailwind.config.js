/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#f8f9ff",
        "surface-lowest": "#ffffff",
        "surface-low": "#eff4ff",
        "surface-container": "#e5eeff",
        "surface-high": "#dce9ff",
        "on-surface": "#0b1c30",
        "on-surface-variant": "#444653",
        outline: "#757684",
        "outline-variant": "#c4c5d5",
        primary: "#00288e",
        "primary-container": "#1e40af",
        "primary-soft": "#dde1ff",
        "on-primary": "#ffffff",
        secondary: "#006c4a",
        "secondary-container": "#82f5c1",
        "on-secondary-container": "#00714e",
        tertiary: "#700006",
        error: "#ba1a1a",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        DEFAULT: "2px",
        md: "4px",
        lg: "6px",
        xl: "8px",
      },
    },
  },
  plugins: [],
};
