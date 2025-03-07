/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html", // Django templates
    "./**/templates/**/*.html", // For multiple apps
    "./static/js/**/*.js", // Optional: If using JS
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
