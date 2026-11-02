/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      colors: {
        // KPIT Colors
        primary: {
          50: '#f6ffe0',
          100: '#eaffb3',
          200: '#d6ff7a',
          300: '#7fff00',
          400: '#b8f21a',
          500: '#a3e500',
          600: '#86bf00',
          700: '#6a9600',
          800: '#4f7000',
          900: '#344a00',
        },
        secondary: {
          500: '#6c25be',
          600: '#5a1ea0',
        },
        accent: {
          500: '#a3e500',
          600: '#86bf00',
        },
        warn: {
          500: '#ff5c6c',
          600: '#e04555',
        },
      },
      fontFamily: {
        sans: ['Inter var', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}