import defaultTheme from 'tailwindcss/defaultTheme'

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
      },
      colors: {
        tg: {
          bg: 'var(--tg-theme-bg-color)',
          text: 'var(--tg-theme-text-color)',
          hint: 'var(--tg-theme-hint-color)',
          link: 'var(--tg-theme-link-color)',
          button: 'var(--tg-theme-button-color)',
          'button-text': 'var(--tg-theme-button-text-color)',
          'secondary-bg': 'var(--tg-theme-secondary-bg-color)',
        },
        ios: {
          green: '#34c759',
        },
      },
      borderRadius: {
        '2xl': '16px',
        'card': '16px',
        'btn': '14px',
        'avatar-sm': '14px',
        'avatar-lg': '20px',
      },
      boxShadow: {
        'soft': '0 1px 3px rgba(0,0,0,0.04)',
      },
      /* Ensure content area does not hide behind fixed navbar */
      spacing: {
        'navbar': '4.5rem',
      },
    },
  },
  plugins: [],
}
