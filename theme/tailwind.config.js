module.exports = {
  content: [
    "./templates/**/*.html",
    "./records/templates/**/*.html",
    "./theme/**/*.css",
  ],
  theme: {
    extend: {
      colors: {
        "site-background": "#EAEBDA",
        "block-background": "#FDFEE9",
        "creamy-main-content": "#FDEFB7",
        "button-blue": "#43B8CF",
        "navbar-button-blue": "#0A4E75",
        "checkmark-green": "#15BC11",
        "error-red": "#D84137",
        "light-red-bg": "#FFEBEE",
        "dark-red-text": "#B71C1C"
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem"
      },
      boxShadow: {
        soft: "0 10px 25px rgba(0,0,0,0.15)"
      }
    }
  },
  plugins: []
}
