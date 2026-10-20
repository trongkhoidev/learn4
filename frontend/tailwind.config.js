/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#edf2ed',
          100: '#eaf1eb',
          200: '#d7e3d9',
          300: '#bdd1c1',
          400: '#9ebaA4',
          500: '#769b83',
          600: '#557961',
          700: '#42624c',
          800: '#2d4938',
          900: '#19352c',
          950: '#10251e',
        }
      },
      fontFamily: {
        sans: ['Geist', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['Geist Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      }
    },
  },
  plugins: [require("tailwindcss-animate")],
};
