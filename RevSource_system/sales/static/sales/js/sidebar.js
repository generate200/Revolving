// Sidebar Toggle Functionality
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebarToggleBtn');

    // Check for saved preference
    const sidebarState = localStorage.getItem('sidebarState') || 'unfolded';
    
    if (sidebarState === 'folded') {
        sidebar.classList.add('folded');
        updateToggleBtn();
    }

    // Toggle sidebar on button click
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('folded');
            
            // Save preference
            const isFolded = sidebar.classList.contains('folded');
            localStorage.setItem('sidebarState', isFolded ? 'folded' : 'unfolded');
            
            // Update button appearance
            updateToggleBtn();
        });
    }

    function updateToggleBtn() {
        const isFolded = sidebar.classList.contains('folded');
        toggleBtn.innerHTML = isFolded ? '<i class="fas fa-chevron-right"></i>' : '<i class="fas fa-chevron-left"></i>';
        toggleBtn.title = isFolded ? 'Expand Sidebar' : 'Collapse Sidebar';
    }

    // Close sidebar on mobile when clicking a link
    const sidebarLinks = document.querySelectorAll('.sidebar-nav a');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth < 768) {
                const overlay = document.getElementById('overlay');
                const menuToggle = document.getElementById('menuToggle');
                
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
                menuToggle.setAttribute('aria-expanded', 'false');
            }
        });
    });
});
