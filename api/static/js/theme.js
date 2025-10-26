// Theme Management
document.addEventListener('DOMContentLoaded', function() {
    // Get the theme toggle button
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    
    // Check for saved theme preference or default to 'dark'
    const savedTheme = localStorage.getItem('theme') || 'dark';
    applyTheme(savedTheme);

    // Add click event to theme toggle button
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            // Get current theme
            const currentTheme = document.documentElement.getAttribute('data-bs-theme');
            // Toggle theme
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            // Update data-color-scheme attribute
            document.documentElement.setAttribute('data-color-scheme', newTheme);
            
            // Apply the theme
            applyTheme(newTheme);
        });
    }
});

function applyTheme(theme) {
    // Update HTML attributes for Bootstrap theming and custom theming
    document.documentElement.setAttribute('data-bs-theme', theme);
    document.documentElement.setAttribute('data-color-scheme', theme);
    document.body.className = theme === 'dark' ? 'theme-dark' : 'theme-light';
    
    // Update theme icon
    const themeIcon = document.getElementById('themeIcon');
    if (themeIcon) {
        themeIcon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    }

    // Update navbar
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        if (theme === 'dark') {
            navbar.classList.add('navbar-dark');
            navbar.classList.remove('navbar-light');
        } else {
            navbar.classList.remove('navbar-dark');
            navbar.classList.add('navbar-light');
        }
    }

    // Save theme preference
    localStorage.setItem('theme', theme);
    
    // Force a repaint to ensure all theme changes are applied
    document.body.style.display = 'none';
    document.body.offsetHeight; // Trigger a reflow
    document.body.style.display = '';
}