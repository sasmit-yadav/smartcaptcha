/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#05070f",
        surface: "#0b0f19",
        surfaceHover: "#111827",
        cfOrange: "#F6821F",
        cfGreen: "#10B981",
        cfRed: "#EF4444",
        cfBlue: "#3B82F6",
        borderMuted: "rgba(255, 255, 255, 0.06)",
        textMuted: "#94A3B8"
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      }
    },
  },
  plugins: [],
}
