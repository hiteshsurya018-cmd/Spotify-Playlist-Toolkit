/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        spotify: '#1DB954',
        ink: '#0B0F14',
        panel: '#111820',
        line: '#23303D',
      },
      boxShadow: {
        soft: '0 20px 60px rgba(0,0,0,0.28)',
      },
    },
  },
  plugins: [],
};
