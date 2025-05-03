// Main JavaScript file for the LMS

// Custom filter for Django templates
// Note: This is just a placeholder, you'll need to implement this in Django
function contains(list, item) {
    return list.includes(item);
}

// Add any additional JavaScript functionality here
document.addEventListener('DOMContentLoaded', function() {
    // Initialize any JavaScript components here
    
    // Example: Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});