/**
 * RevSource ERP - Centralized JavaScript
 * Contains all application JavaScript functionality
 */
document.addEventListener('DOMContentLoaded', function() {  
// Currency Management System

class CurrencyManager {
    constructor() {
        this.currencies = {};
        this.selectedCurrency = 'USD';
        this.baseCurrency = 'USD';
        this.init();
    }

    init() {
        console.log('CurrencyManager initializing...');
        this.loadCurrencies();
        this.createCurrencySelector();
        this.bindEvents();
        
        // Initialize table selector after a short delay to ensure DOM is ready
        setTimeout(() => {
            this.initializeTableSelector();
        }, 100);
        
        console.log('CurrencyManager initialized with currency:', this.selectedCurrency);
    }

    initializeTableSelector() {
        const tableSelect = document.querySelector('#currency-selector-table');
        if (tableSelect) {
            tableSelect.value = this.selectedCurrency;
            console.log('Table selector initialized to:', this.selectedCurrency);
            
            // Bind event for table selector
            tableSelect.addEventListener('change', (e) => {
                console.log('Table selector changed to:', e.target.value);
                this.setSelectedCurrency(e.target.value);
                // Sync other selectors
                const navSelect = document.querySelector('#currency-selector');
                const listSelect = document.querySelector('#currency-selector-list');
                if (navSelect) navSelect.value = e.target.value;
                if (listSelect) listSelect.value = e.target.value;
            });
            
            // Trigger conversion after initialization
            this.convertAllAmounts();
        }
    }

    loadCurrencies() {
        // Load currencies from the JSON script tag
        const currencyScript = document.getElementById('currency-data');
        if (currencyScript) {
            try {
                const currencyData = JSON.parse(currencyScript.textContent);
                this.currencies = currencyData.currencies || {};
                this.baseCurrency = currencyData.baseCurrency || 'USD';
                this.selectedCurrency = localStorage.getItem('selectedCurrency') || this.baseCurrency;
            } catch (e) {
                console.error('Error parsing currency data:', e);
                this.currencies = {};
                this.baseCurrency = 'USD';
                this.selectedCurrency = 'USD';
            }
        } else {
            console.warn('Currency data script not found');
            this.currencies = {};
            this.baseCurrency = 'USD';
            this.selectedCurrency = 'USD';
        }
    }

    createCurrencySelector() {
        // Create currency selector in the top navigation
        const nav = document.querySelector('.site-nav');
        if (nav) {
            const selector = document.createElement('div');
            selector.className = 'currency-selector';
            selector.innerHTML = `
                <select id="currency-selector" class="currency-select">
                    ${Object.entries(this.currencies).map(([code, data]) =>
                        `<option value="${code}" ${code === this.selectedCurrency ? 'selected' : ''}>
                            ${code} (${data.symbol})
                        </option>`
                    ).join('')}
                </select>
            `;

            // Insert before the "Add Product" button or at the end of nav
            const addProductLink = nav.querySelector('.nav-action');
            if (addProductLink) {
                nav.insertBefore(selector, addProductLink);
            } else {
                nav.appendChild(selector);
            }
        }

        // Also add to product list page if it exists
        const productListHeader = document.querySelector('.section-header > div[style*="display: flex"]');
        if (productListHeader) {
            const selector = document.createElement('div');
            selector.className = 'currency-selector';
            selector.innerHTML = `
                <select id="currency-selector-list" class="currency-select">
                    ${Object.entries(this.currencies).map(([code, data]) =>
                        `<option value="${code}" ${code === this.selectedCurrency ? 'selected' : ''}>
                            ${code} (${data.symbol})
                        </option>`
                    ).join('')}
                </select>
            `;
            productListHeader.appendChild(selector);
        }

        // Bind change events for all selectors
        const navSelect = document.querySelector('#currency-selector');
        const listSelect = document.querySelector('#currency-selector-list');
        const tableSelect = document.querySelector('#currency-selector-table');

        console.log('Binding events - navSelect:', !!navSelect, 'listSelect:', !!listSelect, 'tableSelect:', !!tableSelect);

        const handleCurrencyChange = (currencyCode) => {
            console.log('Currency changed to:', currencyCode);
            this.setSelectedCurrency(currencyCode);
            // Sync all selectors
            if (navSelect) navSelect.value = currencyCode;
            if (listSelect) listSelect.value = currencyCode;
            if (tableSelect) tableSelect.value = currencyCode;
        };

        if (navSelect) {
            navSelect.addEventListener('change', (e) => {
                console.log('Nav selector changed');
                handleCurrencyChange(e.target.value);
            });
        }

        if (listSelect) {
            listSelect.addEventListener('change', (e) => {
                console.log('List selector changed');
                handleCurrencyChange(e.target.value);
            });
        }

        if (tableSelect) {
            console.log('Binding table selector event');
            tableSelect.addEventListener('change', (e) => {
                console.log('Table selector changed to:', e.target.value);
                handleCurrencyChange(e.target.value);
            });
        }
    }

    setSelectedCurrency(currencyCode) {
        this.selectedCurrency = currencyCode;
        localStorage.setItem('selectedCurrency', currencyCode);
        this.convertAllAmounts();
    }

    convertAmount(amount, fromCurrency = 'USD', toCurrency = null) {
        if (!toCurrency) toCurrency = this.selectedCurrency;

        // If converting to the same currency, return original
        if (fromCurrency === toCurrency) return amount;

        // Get exchange rates
        const fromRate = this.currencies[fromCurrency]?.exchange_rate || 1;
        const toRate = this.currencies[toCurrency]?.exchange_rate || 1;

        // Convert to base currency first, then to target currency
        const baseAmount = amount / fromRate;
        const convertedAmount = baseAmount * toRate;

        return convertedAmount;
    }

    formatAmount(amount, currencyCode = null) {
        if (!currencyCode) currencyCode = this.selectedCurrency;

        const currency = this.currencies[currencyCode];
        const symbol = currency?.symbol || '$';

        return `${symbol}${amount.toFixed(2)}`;
    }

    convertAllAmounts() {
        console.log('Converting all amounts to:', this.selectedCurrency);
        // Convert all monetary amounts on the page
        document.querySelectorAll('[data-amount]').forEach(element => {
            const originalAmount = parseFloat(element.dataset.amount);
            const originalCurrency = element.dataset.currency || 'USD';
            
            console.log(`Converting ${originalAmount} ${originalCurrency} to ${this.selectedCurrency}`);
            const convertedAmount = this.convertAmount(originalAmount, originalCurrency);
            console.log(`Converted amount: ${convertedAmount}`);
            element.textContent = this.formatAmount(convertedAmount);
        });

        // Update currency symbols in totals and displays
        document.querySelectorAll('[data-currency-display]').forEach(element => {
            element.textContent = this.currencies[this.selectedCurrency]?.symbol || '$';
        });
    }

    bindEvents() {
        // Re-convert amounts when page content changes
        const observer = new MutationObserver(() => {
            setTimeout(() => this.convertAllAmounts(), 100);
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
}

// Journal Entry Form Handler
class JournalEntryForm {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateTotals();
    }

    getCurrencySymbol() {
        const currencySelect = document.getElementById('id_currency');
        if (currencySelect && currencySelect.selectedOptions.length > 0) {
            const selectedOption = currencySelect.selectedOptions[0];
            const text = selectedOption.text;
            const symbolMatch = text.match(/\(([^)]+)\)$/);
            return symbolMatch ? symbolMatch[1] : '$';
        }
        return '$';
    }

    updateTotals() {
        const currencySymbol = this.getCurrencySymbol();
        let totalDebit = 0;
        let totalCredit = 0;

        document.querySelectorAll('.journal-line-form').forEach(function(form) {
            const debitInput = form.querySelector('[name*="debit"]');
            const creditInput = form.querySelector('[name*="credit"]');
            const deleteCheckbox = form.querySelector('[name*="DELETE"]');

            if (deleteCheckbox && !deleteCheckbox.checked) {
                totalDebit += parseFloat(debitInput.value || 0);
                totalCredit += parseFloat(creditInput.value || 0);
            }
        });

        const debitElement = document.getElementById('total-debit');
        const creditElement = document.getElementById('total-credit');

        if (debitElement) debitElement.textContent = currencySymbol + totalDebit.toFixed(2);
        if (creditElement) creditElement.textContent = currencySymbol + totalCredit.toFixed(2);

        const balance = document.getElementById('balance-status');
        if (balance && totalDebit > 0 && totalCredit > 0) {
            balance.style.display = 'block';
            if (Math.abs(totalDebit - totalCredit) < 0.01) {
                balance.innerHTML = '<span style="color: var(--teal); font-weight: 700;">✓ Entry is balanced</span>';
                balance.style.background = 'rgba(20, 184, 166, 0.1)';
            } else {
                balance.innerHTML = '<span style="color: #E02D4C; font-weight: 700;">✗ Not balanced (difference: ' + currencySymbol + Math.abs(totalDebit - totalCredit).toFixed(2) + ')</span>';
                balance.style.background = 'rgba(224, 45, 76, 0.1)';
            }
        } else if (balance) {
            balance.style.display = 'none';
        }
    }

    bindEvents() {
        const form = document.getElementById('journal-form');
        const currencySelect = document.getElementById('id_currency');

        if (form) {
            form.addEventListener('change', () => this.updateTotals());
            form.addEventListener('input', () => this.updateTotals());
        }

        if (currencySelect) {
            currencySelect.addEventListener('change', () => this.updateTotals());
        }
    }
}

// Currency Form Handler
class CurrencyForm {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeState();
    }

    bindEvents() {
        const isBaseCheckbox = document.getElementById('id_is_base');
        if (isBaseCheckbox) {
            isBaseCheckbox.addEventListener('change', () => this.handleBaseCurrencyChange());
        }
    }

    handleBaseCurrencyChange() {
        const isBaseCheckbox = document.getElementById('id_is_base');
        const exchangeRateField = document.getElementById('id_exchange_rate');

        if (isBaseCheckbox && exchangeRateField) {
            if (isBaseCheckbox.checked) {
                exchangeRateField.value = '1.000000';
                exchangeRateField.disabled = true;
            } else {
                exchangeRateField.disabled = false;
            }
        }
    }

    initializeState() {
        this.handleBaseCurrencyChange();
    }
}

// Initialize all components when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize currency manager (global functionality)
    window.currencyManager = new CurrencyManager();

    // Initialize page-specific functionality
    if (document.getElementById('journal-form')) {
        new JournalEntryForm();
    }

    if (document.getElementById('id_is_base')) {
        new CurrencyForm();
    }
});

// Utility functions
function formatCurrency(amount, currencyCode = null) {
    if (window.currencyManager) {
        return window.currencyManager.formatAmount(amount, currencyCode);
    }
    return '$' + amount.toFixed(2);
}

function convertCurrency(amount, fromCurrency = 'USD', toCurrency = null) {
    if (window.currencyManager) {
        return window.currencyManager.convertAmount(amount, fromCurrency, toCurrency);
    }
    return amount;
}
});