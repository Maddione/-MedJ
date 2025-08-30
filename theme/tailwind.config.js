const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  content: [
    '../records/templates/**/*.html',
    './static_src/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        'brand-cream': '#FDFEE9',
        'brand-background': '#EAEBDA',
        'nav-cyan': '#43B8CF',
        'button-blue': '#0A4E75',
        'brand-green': '#15BC11',
        'brand-red': '#D84137',
        'brand-text': '#042A41',
      },
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      boxShadow: {
        'soft': '0 4px 12px rgba(0, 0, 0, 0.08)',
        'card': '0 2px 8px rgba(0, 0, 0, 0.06)',
      }
    }
  },
  plugins: [
      require('@tailwindcss/forms'),
  ]
}