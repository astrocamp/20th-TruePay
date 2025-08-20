// static/scripts/menu.js
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    const toggleBtn  = document.getElementById("menu-toggle");
    const mobileMenu = document.getElementById("mobile-menu");
    const navBrand   = document.getElementById("nav-brand");

    if (!toggleBtn || !mobileMenu || !navBrand) return;

    const closeMenu = () => {
      if (!mobileMenu.classList.contains("hidden")) {
        mobileMenu.classList.add("hidden");
        navBrand.classList.remove("hidden");
        toggleBtn.setAttribute("aria-expanded", "false");
      }
    };

    toggleBtn.addEventListener("click", function (e) {
      e.preventDefault();
      const isHidden = mobileMenu.classList.toggle("hidden");
      navBrand.classList.toggle("hidden", !isHidden);
      toggleBtn.setAttribute("aria-expanded", String(!isHidden));
    });

    mobileMenu.addEventListener("click", function (e) {
      const a = e.target.closest("a");
      if (a) closeMenu();
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth >= 768) {
        mobileMenu.classList.add("hidden");
        navBrand.classList.remove("hidden");
        toggleBtn.setAttribute("aria-expanded", "false");
      }
    });
  });
})();