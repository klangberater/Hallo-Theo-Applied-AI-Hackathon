import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Fletcher design system tokens — verbatim from docs/fletcher-design-system.html
        paper: {
          50:  '#FBFAF7',
          100: '#F5F3EE',
          200: '#ECE9E2',
          300: '#D9D5CB',
          400: '#B5AFA1',
          500: '#8A8475',
          600: '#5F5A4E',
          700: '#3F3B33',
          800: '#26241F',
          900: '#161513',
        },
        teal: {
          50:  '#ECFDF8',
          100: '#D1FAEE',
          200: '#A7F0DD',
          300: '#6FE0C5',
          400: '#36C9AA',
          500: '#14B295',
          600: '#0F8E78',
          700: '#0E7060',
          800: '#0D584E',
          900: '#0A3F39',
        },
        // status palettes already exist in tailwind defaults (red/amber/green/blue);
        // we just use the standard 50/100/200/500/600/700 shades.
      },
      fontFamily: {
        sans:  ['Geist', 'system-ui', 'sans-serif'],
        serif: ['Fraunces', 'Georgia', 'serif'],
        mono:  ['"JetBrains Mono"', 'SF Mono', 'Menlo', 'monospace'],
      },
      fontSize: {
        // Design-system scale — 17px body floor for the Hausverwalter audience
        xs:   ['13px', { lineHeight: '1.4' }],
        sm:   ['15px', { lineHeight: '1.5' }],
        base: ['17px', { lineHeight: '1.55' }],
        md:   ['19px', { lineHeight: '1.5' }],
        lg:   ['22px', { lineHeight: '1.35' }],
        xl:   ['28px', { lineHeight: '1.2' }],
        '2xl':['36px', { lineHeight: '1.15' }],
      },
      borderRadius: {
        sm:   '6px',
        md:   '10px',
        lg:   '14px',
        xl:   '20px',
      },
      boxShadow: {
        xs: '0 1px 2px 0 rgba(22,21,19,.04)',
        sm: '0 1px 3px 0 rgba(22,21,19,.06), 0 1px 2px 0 rgba(22,21,19,.04)',
        md: '0 4px 8px -2px rgba(22,21,19,.08), 0 2px 4px -2px rgba(22,21,19,.04)',
        lg: '0 12px 24px -8px rgba(22,21,19,.12), 0 4px 8px -4px rgba(22,21,19,.06)',
      },
    },
  },
  plugins: [],
};

export default config;
