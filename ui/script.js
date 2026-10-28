// DOM Elements
const compareBtn = document.getElementById('compareBtn');
const compareCountries = document.getElementById('compareCountries');
const compareMetric = document.getElementById('compareMetric');
const comparePlot = document.getElementById('comparePlot');
const loading = document.getElementById('loading');
const errorMessage = document.getElementById('errorMessage');
const countriesList = document.getElementById('countriesList');
const groupsList = document.getElementById('groupsList');
const countryCount = document.getElementById('countryCount');
const groupCount = document.getElementById('groupCount');

// API base URL (works for both local and Render)
const API_BASE = window.location.origin;

// Initialize the page
document.addEventListener('DOMContentLoaded', async () => {
    await loadCountries();
    setupEventListeners();
});

// Load available countries from API
async function loadCountries() {
    try {
        const response = await fetch(`${API_BASE}/countries`);
        if (!response.ok) throw new Error('Failed to load countries');

        const data = await response.json();

        // Populate country dropdown
        data.countries.forEach(country => {
            const option = document.createElement('option');
            option.value = country.code;
            option.textContent = country.name;
            compareCountries.appendChild(option);
        });

        // Populate summary lists
        data.countries.forEach(country => {
            const li = document.createElement('li');
            li.textContent = country.name;
            countriesList.appendChild(li);
        });
        countryCount.textContent = data.countries.length;

        data.groups.forEach(group => {
            const li = document.createElement('li');
            li.textContent = group;
            groupsList.appendChild(li);
        });
        groupCount.textContent = data.groups.length;

    } catch (error) {
        showError(`Failed to load countries: ${error.message}`);
    }
}

// Set up event listeners
function setupEventListeners() {
    compareBtn.addEventListener('click', generateComparison);
}

// Generate comparison plot
async function generateComparison() {
    // Get selected values
    const selectedCountries = Array.from(compareCountries.selectedOptions)
        .map(option => option.value);

    const selectedMetric = compareMetric.value;

    // Validate input
    if (selectedCountries.length === 0) {
        showError('Please select at least one country');
        return;
    }

    if (selectedCountries.length > 5) {
        showError('Please select a maximum of 5 countries');
        return;
    }

    // Clear previous errors
    hideError();

    // Show loading state
    showLoading();

    try {
        // Call API
        const response = await fetch(
            `${API_BASE}/plot/compare?countries=${selectedCountries.join(',')}&metric=${encodeURIComponent(selectedMetric)}`
            //`${API_BASE}/plot/compare?countries=${encodeURIComponent(selectedCountries.join(','))}&metric=${selectedMetric}`
        );

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to generate plot');
        }

        // Get plot as blob
        const blob = await response.blob();
        const plotUrl = URL.createObjectURL(blob);

        // Display plot
        comparePlot.innerHTML = `
            <div class="text-center">
                <img src="${plotUrl}" alt="Comparison Plot" class="img-fluid">
                <p class="mt-2 text-muted">
                    <strong>Countries:</strong> ${selectedCountries.join(', ')} |
                    <strong>Metric:</strong> ${formatMetricName(selectedMetric)}
                </p>
            </div>
        `;

    } catch (error) {
        showError(`Error: ${error.message}`);
    } finally {
        hideLoading();
    }
}

// Helper functions
function showLoading() {
    compareBtn.disabled = true;
    compareBtn.querySelector('.spinner-border').classList.remove('d-none');
    loading.style.display = 'block';
    comparePlot.innerHTML = '';
}

function hideLoading() {
    compareBtn.disabled = false;
    compareBtn.querySelector('.spinner-border').classList.add('d-none');
    loading.style.display = 'none';
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

function hideError() {
    errorMessage.style.display = 'none';
}

function formatMetricName(metric) {
    return metric
        .replace(/_/g, ' ')
        .replace(/pct/g, '%')
        .replace(/mio/g, 'Million ')
        .replace(/eur/g, 'EUR')
        .replace(/pps/g, 'PPS')
        .replace(/per head/g, 'per Head')
        .toUpperCase();
}