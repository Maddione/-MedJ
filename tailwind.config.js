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
        'creamy-bg': '#FDEFB7',
        'button-blue': '#43B8CF',
        'navbar-button-blue': '#0A4E75',
        'checkmark-green': '#15BC11',
        'error-red': '#D84137',
        'light-red-bg': '#FFEBEE',
        'dark-red-text': '#B71C1C',
      },
    }
  },
  safelist: [ // NEW: Safelist to ensure these classes are always generated
    'bg-site-background',
    'bg-block-background',
    'bg-creamy-bg',
    'bg-button-blue',
    'bg-navbar-button-blue',
    'bg-checkmark-green',
    'bg-error-red',
    'bg-light-red-bg',
    'bg-dark-red-text',
    'text-white', // Ensure text-white is always available
    'text-gray-700', // Common text colors
    'text-gray-800',
    'text-gray-600',
    'text-red-700',
    'text-red-600',
    'text-blue-500',
    'text-blue-800',
    // You can add more classes here if they are dynamically added and not appearing
    // e.g., 'hover:bg-blue-600', 'focus:ring-blue-500', etc.
  ],
  plugins: [],
}