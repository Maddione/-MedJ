module.exports = {
  content: [
    "./records/templates/**/*.html",
    "./records/templates/main/*.html",
    "./records/templates/basetemplates/*.html",
    "./records/templates/auth/*.html",
    "./records/templates/subpages/*.html",
    "./medj/templates/**/*.html",
    "./templates/**/*.html",
    "./records/**/*.js",
    "./static/js/**/*.js",
    "./theme/static_src/**/*.js",
    "./records/**/*.py",
    "./theme/static_src/**/*.css",
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
