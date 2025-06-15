/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './MedJ/templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        'site-background': '#EAEBDA',
        'block-background': '#FDFEE9',
        'button-blue': '#43B8CF',
        'navbar-button-blue': '#0A4E75',
        'checkmark-green': '#15BC11',
        'error-red': '#D84137',
        'light-red-bg': '#FFEBEE',
        'dark-red-text': '#B71C1C',
      },
    }
  },
  plugins: [],
}