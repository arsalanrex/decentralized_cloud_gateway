document.addEventListener('DOMContentLoaded', function() {
    // Resource search functionality
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    const typeFilter = document.getElementById('resourceTypeFilter');
    const resourceCards = document.querySelectorAll('.resource-card');

    // Search function
    function filterResources() {
        const searchTerm = searchInput.value.toLowerCase();
        const filterType = typeFilter.value;

        resourceCards.forEach(card => {
            const cardTitle = card.querySelector('.card-title').textContent.toLowerCase();
            const cardType = card.dataset.type;

            // Check if card matches both search term and filter type
            const matchesSearch = cardTitle.includes(searchTerm);
            const matchesType = filterType === '' || cardType === filterType;

            // Show or hide the card
            if (matchesSearch && matchesType) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }

    // Add event listeners
    if (searchButton) {
        searchButton.addEventListener('click', filterResources);
    }

    if (searchInput) {
        searchInput.addEventListener('keyup', function(event) {
            if (event.key === 'Enter') {
                filterResources();
            }
        });
    }

    if (typeFilter) {
        typeFilter.addEventListener('change', filterResources);
    }

    // Hours input calculation for borrowing modal
    const hoursInputs = document.querySelectorAll('input[name="hours"]');

    hoursInputs.forEach(input => {
        input.addEventListener('input', function() {
            // Find the closest modal which contains this input
            const modal = this.closest('.modal');
            if (!modal) return;

            // Find the credit rate element in this modal
            const creditRate = parseFloat(modal.querySelector('.alert-info').textContent.match(/Cost: (\d+(?:\.\d+)?) credits\/hour/)[1]);
            const totalCost = this.value * creditRate;

            // Update the modal with calculated cost if there's an element for it
            const costElement = modal.querySelector('.calculated-cost');
            if (costElement) {
                costElement.textContent = `Total cost: ${totalCost.toFixed(2)} credits`;
            }
        });
    });

    // Resource monitoring simulation (for dashboard)
    // This is just a simple example to show some dynamic elements
    function updateResourceMetrics() {
        const metricElements = document.querySelectorAll('.resource-metric');

        metricElements.forEach(element => {
            // Simple random fluctuation for demo purposes
            const currentValue = parseFloat(element.textContent);
            const fluctuation = (Math.random() - 0.5) * 10; // Random value between -5 and 5
            const newValue = Math.max(0, currentValue + fluctuation).toFixed(1);

            // Update with animation
            element.textContent = newValue;
            element.classList.add('updated');

            // Remove animation class after transition completes
            setTimeout(() => {
                element.classList.remove('updated');
            }, 1000);
        });
    }

    // If we're on the dashboard, update metrics periodically
    if (document.querySelector('.resource-metric')) {
        // Update every 10 seconds
        setInterval(updateResourceMetrics, 10000);
    }

    // Initialize tooltips and popovers if Bootstrap is loaded
    if (typeof bootstrap !== 'undefined') {
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));

        const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
        popovers.forEach(popover => new bootstrap.Popover(popover));
    }
});