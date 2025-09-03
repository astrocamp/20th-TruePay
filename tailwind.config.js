/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./templates/**/*.html",
    "./pages/templates/**/*.html",
    "./pages/**/*.html",
    "./merchant_account/**/*.html",
    "./customers_account/**/*.html", 
    "./merchant_marketplace/**/*.html",
    "./public_store/**/*.html",
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
        cis: {
          primary: "#003d82",     // CIS 主色 - 深藍
          primaryHover: "#002a5c", // CIS 主色 Hover
          secondary: "#00a651",   // CIS 次要色 - 綠色
          secondaryHover: "#007d3c", // CIS 次要色 Hover
          accent: "#ff6b35",      // CIS 強調色 - 橙色
          accentHover: "#e5572e", // CIS 強調色 Hover
        },
      },
    },
  },
  plugins: [],
}