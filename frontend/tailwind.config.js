/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Plus Jakarta Sans'", 'ui-sans-serif', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        sans:    ["'Inter'", "'Plus Jakarta Sans'", 'ui-sans-serif', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      colors: {
        // M1M brand palette
        m1m: {
          teal:          '#1a5c4a',
          'teal-dark':   '#0f3d30',
          green:         '#25D366',
          'green-bubble':'#d9fdd3',
          'green-text':  '#006b3c',
          orange:        '#E8792A',
          'orange-dark': '#c8621d',
          chat:          '#ece5dd',
          'chat-dot':    '#cdbfb2',
        },
        // Onboarding brand
        brand: {
          50:  '#f0fdf8',
          100: '#ccfbec',
          200: '#99f6da',
          300: '#5eead4',
          400: '#2dd4b8',
          500: '#14b88a',
          600: '#0d9668',
          700: '#0a7a52',
          800: '#0b6143',
          900: '#0c4f38',
          950: '#042f22',
        },
      },
      borderRadius: {
        'bubble': '18px',
        'chip':   '9999px',
        '2xl':    '1rem',
        '3xl':    '1.5rem',
        '4xl':    '2rem',
      },
      boxShadow: {
        'bubble':     '0 1px 2px rgba(0,0,0,0.12)',
        'card':       '0 2px 8px rgba(0,0,0,0.10)',
        'composer':   '0 -1px 8px rgba(0,0,0,0.08)',
        'glass':      '0 8px 32px 0 rgba(31,38,135,0.10)',
        'onboard':    '0 24px 64px rgba(0,0,0,0.14)',
        'soft':       '0 4px 24px rgba(0,0,0,0.08)',
        'glow':       '0 0 40px rgba(20,184,138,0.18)',
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #0d9668 0%, #14b88a 50%, #2dd4b8 100%)',
        'hero-gradient':  'linear-gradient(160deg, #042f22 0%, #0a7a52 40%, #0d9668 100%)',
        'card-gradient':  'linear-gradient(145deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%)',
      },
      animation: {
        'fade-up':     'fadeUp 0.5s ease both',
        'fade-in':     'fadeIn 0.4s ease both',
        'slide-right': 'slideRight 0.4s ease both',
        'pulse-slow':  'pulse 3s ease-in-out infinite',
        'float':       'float 6s ease-in-out infinite',
        'shimmer':     'shimmer 2s linear infinite',
      },
      keyframes: {
        fadeUp:    { from: { opacity: '0', transform: 'translateY(20px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        fadeIn:    { from: { opacity: '0' },                                 to: { opacity: '1' } },
        slideRight:{ from: { opacity: '0', transform: 'translateX(-16px)' }, to: { opacity: '1', transform: 'translateX(0)' } },
        float:     { '0%,100%': { transform: 'translateY(0)' },              '50%': { transform: 'translateY(-10px)' } },
        shimmer:   { from: { backgroundPosition: '-200% 0' },               to:   { backgroundPosition: '200% 0' } },
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [],
}

