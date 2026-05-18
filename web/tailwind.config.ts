import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          bg: "#f3ede2",
          surface: "#fffdf8",
          low: "#ece3d4",
          high: "#ded1bd",
          line: "#c6b79f",
          text: "#23201b",
          muted: "#6f685d",
          primary: "#23473d",
          primarySoft: "#dee9e2",
          tertiary: "#8b5d3b",
          errorSoft: "#f7dfd9",
          errorText: "#93000a"
        }
      },
      fontFamily: {
        headline: ["var(--font-newsreader)"],
        body: ["var(--font-newsreader)"],
        label: ["var(--font-inter)"]
      },
      boxShadow: {
        paper: "0 18px 40px rgba(77, 60, 31, 0.12), 0 2px 6px rgba(35, 32, 27, 0.06)"
      },
      maxWidth: {
        reading: "52rem",
        shell: "78rem"
      }
    }
  },
  plugins: []
};

export default config;
