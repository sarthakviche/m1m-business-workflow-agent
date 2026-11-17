/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
      },
      colors: {
        wa: {
          // WhatsApp green palette
          green:       '#25D366',
          'green-dark':'#128C7E',
          'green-teal':'#075E54',
          // Chat background
          chat:        '#efeae2',
          // Bubble colours
          'bubble-out':'#d9fdd3',
          'bubble-in': '#ffffff',
          // Header/footer
          header:      '#128C7E',
          'input-bg':  '#ffffff',
          // Ticks
          tick:        '#53bdeb',
        },
      },
      boxShadow: {
        bubble: '0 1px 2px rgba(0,0,0,0.15)',
        card:   '0 2px 8px rgba(0,0,0,0.12)',
      },
      borderRadius: {
        bubble: '7.5px',
        chip:   '9999px',
      },
    },
  },
  plugins: [],
}
