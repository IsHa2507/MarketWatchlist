/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        surface: {
          DEFAULT: '#0f1117',
          card: '#161b27',
          elevated: '#1e2535',
          border: '#252d3d',
        },
        accent: {
          DEFAULT: '#3b82f6',
          hover: '#2563eb',
        },
        critical: {
          DEFAULT: '#ef4444',
          bg: '#1f0f0f',
          border: '#7f1d1d',
        },
        important: {
          DEFAULT: '#f97316',
          bg: '#1c1208',
          border: '#7c2d12',
        },
        watching: {
          DEFAULT: '#eab308',
          bg: '#1a1700',
          border: '#713f12',
        },
        normal: {
          DEFAULT: '#22c55e',
          bg: '#0a1f12',
          border: '#14532d',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
