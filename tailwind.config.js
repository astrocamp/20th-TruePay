/** @type {import('tailwindcss').Config} */
export default {
  safelist: [
    'bg-brand-grayLight',
    'bg-brand-blue',
    'bg-brand-blueHover',
    'hover:bg-brand-blueHover',
    'text-cis-secondary',
    'hover:bg-cis-secondary-hover',
    'border-cis-secondary',
    'text-cis-accent',
    'hover:bg-cis-accent-hover',
    'border-cis-accent',
  ],
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
          background: "#FDFBF5", // 米色背景
          text: "#4A4A4A",       // 深灰文字
          white: "#FFFFFF",     // 純白
          grayLight: "#F5F5F7", // 淺灰
          grayBorder: "#D2D2D7" // 分隔線灰
        },
        cis: {
          primary: "#20C997",      // 主色 - 湖水綠/Tiffany 綠
          primaryHover: "#1BAA80",  // 主色 Hover
          secondary: "#F39C12",    // 次要色 - 沿用 Logo 的亮黃色
          secondaryHover: "#E67E22",// 次要色 Hover
          accent: "#ff6b35",       // 強調色 - 橙色 (可保留或修改)
          accentHover: "#e5572e",  // 強調色 Hover
        },
      },
    },
  },
  plugins: [],
}