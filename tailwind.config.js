/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        razor: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#b9dffe',
          300: '#7cc5fd',
          400: '#36a8fa',
          500: '#0c8cee',
          600: '#006ecb',
          700: '#0157a4',
          800: '#054a86',
          900: '#0a3f6f',
          950: '#07284a',
        },
        slate: {
          850: '#151e2e',
          900: '#0f172a',
          950: '#080d1a',
        },
        emerald: {
          450: '#10b981',
          500: '#059669',
        }
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(12, 140, 238, 0.2), 0 0 10px rgba(12, 140, 238, 0.1)' },
          '100%': { boxShadow: '0 0 20px rgba(12, 140, 238, 0.6), 0 0 30px rgba(16, 185, 129, 0.4)' },
        }
      }
    },
  },
  plugins: [],
}
