/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./templates/**/*.html",
    "./pages/templates/**/*.html", 
    "./src/**/*.{js,ts}",
    "./static/**/*.{js,ts}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: "#0056B3",      // 主深藍
          blueHover: "#00408A", // Hover 深藍
          black: "#000000",     // 主黑
          white: "#FFFFFF",     // 主白
          grayDark: "#333333",  // 深灰
          grayLight: "#F5F5F7", // 淺灰
          grayBorder: "#D2D2D7" // 分隔線灰
        },
      },
    },
  },
  plugins: [],
}