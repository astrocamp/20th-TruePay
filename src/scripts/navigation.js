// Navigation functionality
document.addEventListener('DOMContentLoaded', function() {
    // Smooth scroll for navigation links
    document.querySelectorAll('a[href*="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            // Check if the link is to the homepage from another page
            const currentPath = window.location.pathname;
            const linkPath = this.pathname;
            const linkHash = this.hash;

            if (currentPath === linkPath) {
                e.preventDefault();
                const target = document.querySelector(linkHash);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
            // If it's a link to the homepage from another page, let the default browser behavior handle it.
        });
    });

    // Update active navigation link on scroll (only for homepage)
    if (window.location.pathname === '/' || window.location.pathname.includes('home')) {
        window.addEventListener('scroll', function() {
            const sections = document.querySelectorAll('section[id]');
            const navLinks = document.querySelectorAll('.nav-links a');

            let current = '';
            sections.forEach(section => {
                const sectionTop = section.offsetTop - 100;
                if (scrollY >= sectionTop) {
                    current = section.getAttribute('id');
                }
            });

            navLinks.forEach(link => {
                link.classList.remove('active');
                // Check href that ends with the anchor
                if (link.href.endsWith('#' + current)) {
                    link.classList.add('active');
                }
            });
        });
    }
});