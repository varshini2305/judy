/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Precise, technical dark palette.
        ink: {
          900: "#0a0c10", // app background
          800: "#0f1219", // panels
          700: "#161b25", // raised
          600: "#1f2632", // borders/hover
          500: "#2a3340",
        },
        fog: {
          400: "#8b96a8", // muted text
          300: "#aab4c4",
          200: "#d4dae3", // body text
          100: "#eef1f6", // headings
        },
        // One accent for improved/correct, one for error/regressed.
        good: { DEFAULT: "#34d399", dim: "#0f3b2e" },
        bad: { DEFAULT: "#fb7185", dim: "#3d1620" },
        accent: { DEFAULT: "#7c9cff", dim: "#1b2540" },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
