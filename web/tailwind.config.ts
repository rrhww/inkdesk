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
          bg: "#f8f9fa",
          surface: "#ffffff",
          low: "#f3f4f5",
          high: "#e7e8e9",
          line: "#bcc9c6",
          text: "#191c1d",
          muted: "#687573",
          primary: "#00685f",
          primarySoft: "#e8f6f4",
          tertiary: "#924628",
          errorSoft: "#ffdad6",
          errorText: "#93000a"
        }
      },
      fontFamily: {
        headline: ["var(--font-manrope)"],
        body: ["var(--font-newsreader)"],
        label: ["var(--font-inter)"]
      },
      boxShadow: {
        paper: "0 18px 40px rgba(25, 28, 29, 0.06)"
      },
      maxWidth: {
        reading: "52rem",
        shell: "72rem"
      }
    }
  },
  plugins: []
};

export default config;
