/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    fontFamily: {
      body: ['M PLUS Rounded 1c'],
    },
    extend: {
      transitionProperty: {
        width: 'width',
        height: 'height',
      },
      animation: {
        fastPulse: 'pulse 0.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      colors: {
        'aws-squid-ink': {
          light: '#232F3E',
          dark: '#171717',
        },
        'aws-sea-blue': {
          light: '#005276',
          dark: '#757575',
        },
        'aws-sea-blue-hover': {
          light: '#003550',
          dark: '#5b5b5b',
        },
        'aws-aqua': '#007faa',
        'aws-lab': '#38ef7d',
        'aws-mist': '#9ffcea',
        'aws-font-color': {
          light: '#232F3E',
          dark: '#cacaca',
          gray: '#909193',
          blue: '#276cc6',
        },
        'aws-font-color-white': {
          light: '#ffffff',
          dark:'#ececec',
        },
        'aws-ui-color': {
          dark: '#151515',
        },
        'aws-paper': {
          light: '#f1f3f3',
          dark: '#212121',
        },
        // red-400 is for text in dark mode, where the default red is 3.3:1.
        red: { DEFAULT: '#dc2626', 400: '#f87171' },
        // Links in dark mode; aws-sea-blue-dark is only 3.5:1 there.
        'aws-link-dark': '#8ab4f8',
        'light-red': '#fee2e2',
        yellow: '#f59e0b',
        'light-yellow': '#fef9c3',
        // Readable as small text on the light paper background (WCAG AA).
        'dark-gray': '#5b616e',
        gray: '#9ca3af',
        'light-gray': '#e5e7eb',
      },
    },
  },
  // eslint-disable-next-line no-undef
  plugins: [require('@tailwindcss/typography'), require('tailwind-scrollbar')],
};
