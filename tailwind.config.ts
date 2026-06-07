import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Warm paper canvas (Swiss/editorial), near-black ink, one cobalt accent.
        paper: "#F1EFE9",
        panel: "#FBFAF6",
        ink: "#111114",
        muted: "#56585F",
        line: "#D8D6CD",
        cobalt: {
          DEFAULT: "#2C4EE6",
          50: "#ECEFFE",
          100: "#DBE1FD",
          200: "#B7C4FB",
          300: "#8B9EF6",
          400: "#5C74EF",
          500: "#3C58EA",
          600: "#2C4EE6",
          700: "#2240C4",
          800: "#1E369C",
          900: "#1B2F7C",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Arial Narrow", "Arial", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: [
          "var(--font-sans)",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      maxWidth: {
        content: "82rem",
      },
      letterSpacing: {
        label: "0.18em",
        wide2: "0.26em",
      },
      borderRadius: {
        // Brutalist/Swiss: hard edges everywhere by default.
        none: "0",
      },
      boxShadow: {
        hard: "5px 5px 0 0 #111114",
        "hard-cobalt": "5px 5px 0 0 #2C4EE6",
      },
      keyframes: {
        blink: {
          "0%, 49%": { opacity: "1" },
          "50%, 100%": { opacity: "0" },
        },
      },
      animation: {
        blink: "blink 1.1s step-end infinite",
      },
    },
  },
  plugins: [],
};

export default config;
