import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        risk: {
          low: "#16a34a",
          medium: "#eab308",
          high: "#f97316",
          critical: "#dc2626",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
