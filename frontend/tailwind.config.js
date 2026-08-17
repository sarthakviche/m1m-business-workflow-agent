/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        // M1M brand palette — deep teal header, green bubbles, orange accents
        m1m: {
          teal:      '#1a5c4a',   // header background
          'teal-dark': '#0f3d30', // header gradient / shadow
          green:     '#25D366',   // WhatsApp green (mic button, active chips)
          'green-bubble': '#d9fdd3', // user message bubble background
          'green-text': '#006b3c',   // active chip text / borders
          orange:    '#E8792A',   // M1M logo, Download PDF button
          'orange-dark': '#c8621d',  // button hover
          chat:      '#ece5dd',   // chat area background (WhatsApp warm beige)
          'chat-dot': '#cdbfb2',  // subtle dot pattern
        },
      },
      borderRadius: {
        'bubble': '18px',
        'chip': '9999px',
      },
      boxShadow: {
        'bubble': '0 1px 2px rgba(0,0,0,0.12)',
        'card': '0 2px 8px rgba(0,0,0,0.10)',
        'composer': '0 -1px 8px rgba(0,0,0,0.08)',
      },
    },
  },
  plugins: [],
}
