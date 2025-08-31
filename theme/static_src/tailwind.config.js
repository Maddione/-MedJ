module.exports = {
  content: [
    "./records/templates/**/*.html",
    "./medj/templates/**/*.html",
    "./templates/**/*.html",
    "./records/**/*.js",
    "./static/js/**/*.js",
    "./theme/static_src/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        sitebg: "#EAEBDA",
        blockbg: "#FDFEE9",
        primary: "#43B8CF",
        primaryDark: "#0A4E75",
        success: "#15BC11",
        danger: "#D84137"
      }
    }
  },
  plugins: []
}
