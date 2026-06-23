/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        abyss: '#05080f',
        navy: {
          950: '#05080f',
          900: '#080e1c',
          800: '#0c1220',
          700: '#12213a',
          600: '#1a3050',
        },
        gold: {
          200: '#fdf3c0',
          300: '#f5dfa0',
          400: '#e8c44a',
          500: '#c9a227',
          600: '#a07d15',
        },
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        body:    ['"Syne"', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'fade-up':    'fadeUp 0.5s ease both',
        'fade-in':    'fadeIn 0.4s ease both',
        'shimmer':    'shimmer 2s infinite',
        'spin-slow':  'spin-slow 8s linear infinite',
        'float':      'float 4s ease-in-out infinite',
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        fadeUp:      { from: { opacity: 0, transform: 'translateY(20px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        fadeIn:      { from: { opacity: 0 }, to: { opacity: 1 } },
        shimmer:     { '0%': { backgroundPosition: '-400px 0' }, '100%': { backgroundPosition: '400px 0' } },
        'spin-slow': { from: { transform: 'rotate(0deg)' }, to: { transform: 'rotate(360deg)' } },
        float:       { '0%, 100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-6px)' } },
        'glow-pulse':{ '0%, 100%': { opacity: '0.4' }, '50%': { opacity: '0.9' } },
      },
    },
  },
  plugins: [],
}
