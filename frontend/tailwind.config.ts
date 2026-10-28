import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        lab: {
          900: "#0b0f19",
          850: "#111827",
          800: "#1a2234",
          700: "#243048",
          600: "#334155",
          accent: "#10b981",
          cyan: "#06b6d4",
          amber: "#f59e0b"
        }
      }
    },
  },
  plugins: [],
};

export default config;
