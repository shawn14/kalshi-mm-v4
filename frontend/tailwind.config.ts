import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // iOS dark mode system backgrounds
        bg:       "#000000",         // systemBackground dark
        surface:  "#1c1c1e",         // secondarySystemBackground dark
        surface2: "#2c2c2e",         // tertiarySystemBackground dark
        border:   "rgba(84,84,88,0.65)", // separator dark
        muted:    "#3a3a3c",
        "muted-fg": "#8e8e93",       // systemGray dark
        fg:       "#ffffff",
        "fg-2":   "rgba(255,255,255,0.88)",  // secondaryLabel dark
        "fg-3":   "rgba(255,255,255,0.60)",  // tertiaryLabel dark

        // iOS system colors (dark mode variants)
        blue:     "#0a84ff",   // systemBlue dark
        green:    "#30d158",   // systemGreen dark
        red:      "#ff453a",   // systemRed dark
        orange:   "#ff9f0a",   // systemOrange dark
        yellow:   "#ffd60a",   // systemYellow dark
        purple:   "#bf5af2",   // systemPurple dark
        indigo:   "#5e5ce6",   // systemIndigo dark
        teal:     "#40cbe0",   // systemTeal dark

        // Semantic fills (translucent)
        "fill-1": "rgba(120,120,128,0.36)", // primary fill dark
        "fill-2": "rgba(120,120,128,0.32)",
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "'SF Pro Display'", "system-ui", "sans-serif"],
        mono: ["'SF Mono'", "'JetBrains Mono'", "'Fira Code'", "monospace"],
      },
      borderRadius: {
        xl: "16px",
        lg: "12px",
        md: "10px",
        sm: "6px",
      },
      fontSize: {
        "2xs": "10px",
        xs:    "12px",
        sm:    "13px",
        base:  "15px",
        lg:    "17px",
        xl:    "20px",
        "2xl": "24px",
        "3xl": "30px",
      },
    },
  },
  plugins: [],
};

export default config;
