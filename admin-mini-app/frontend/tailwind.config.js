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
        app: {
          accent: '#007aff',
          'text-primary': '#1a1a2e',
          'text-secondary': '#8e8e93',
          'surface-tertiary': '#f5f5f7',
          'success-bg': '#e8f5e9',
          'success-text': '#2e7d32',
          'success-icon': '#4caf50',
          'error-bg': '#fce4ec',
          'error-text': '#c62828',
          'warning-bg': '#fff3e0',
          'warning-text': '#e65100',
          'info-bg': '#e3f2fd',
          'info-text': '#1565c0',
          'purple-bg': '#f3e5f5',
          'toggle-on': '#34c759',
          'toggle-off': '#e9e9eb',
        },
      },
      borderRadius: {
        '2xl': '16px',
        'card': '16px',
        'btn': '14px',
        'avatar-sm': '14px',
        'avatar-lg': '22px',
      },
      boxShadow: {
        'soft': '0 1px 3px rgba(0,0,0,0.04)',
        'chip': '0 1px 2px rgba(0,0,0,0.04)',
      },
      /* Ensure content area does not hide behind fixed navbar */
      spacing: {
        'navbar': '4.5rem',
      },
    },
  },
  plugins: [],
}
