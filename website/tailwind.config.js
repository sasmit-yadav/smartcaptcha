/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Dark console canvas — the whole product lives on this, not just chrome
        ink: '#f2f3f5',
        mute: '#98a1ad',
        stone: '#6b7280',
        canvas: '#08090b',
        surface: '#111318',
        surfaceSoft: '#15181f',
        surfaceElevated: '#1b1f27',
        hairline: 'rgba(255,255,255,0.09)',
        hairlineStrong: 'rgba(255,255,255,0.16)',

        // Single accent — VeilProof Blue. Precious resource: CTAs, active states, tags.
        primary: '#2f6bff',
        primaryDark: '#1d4fd6',
        primarySoft: 'rgba(47,107,255,0.14)',

        // Semantic
        success: '#2fbf71',
        successSoft: 'rgba(47,191,113,0.12)',
        danger: '#f2554a',
        dangerSoft: 'rgba(242,85,74,0.12)',
        warning: '#e2913b',
        warningSoft: 'rgba(226,145,59,0.12)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      spacing: {
        section: '96px',
      },
    },
  },
  plugins: [],
}
