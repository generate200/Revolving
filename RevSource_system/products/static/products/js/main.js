/**
 * RevSource ERP - Centralized JavaScript
 * Contains all application JavaScript functionality
 */
document.addEventListener('DOMContentLoaded', function() {  
// Currency Management System
const selector = document.getElementById('currency-selector-table');
const menuToggle = document.getElementById("menuToggle");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");

    if (selector) {
        selector.addEventListener('change', function() {
            const currency = this.value;
            const url = new URL(window.location.href);
            url.searchParams.set('currency', currency);
            window.location.href = url.toString();
        });
    }
        const currencySelect = document.getElementById('id_currency');
    const exchangeRateInput = document.getElementById('id_exchange_rate');

    const totalDebitEl = document.getElementById('total-debit');
    const totalCreditEl = document.getElementById('total-credit');
    const balanceStatus = document.getElementById('balance-status');

    if (!currencySelect) return; // stop if not on journal page

    let currentSymbol = '$';

    function getSelectedCurrencyData() {
        const selected = currencySelect.options[currencySelect.selectedIndex];

        return {
            symbol: selected.dataset.symbol || '$',
            rate: parseFloat(selected.dataset.rate) || 1.0
        };
    }

    function calculateTotals() {
        let totalDebit = 0;
        let totalCredit = 0;

        document.querySelectorAll('.debit-input').forEach(input => {
            totalDebit += parseFloat(input.value) || 0;
        });

        document.querySelectorAll('.credit-input').forEach(input => {
            totalCredit += parseFloat(input.value) || 0;
        });

        totalDebitEl.innerText = `${currentSymbol}${totalDebit.toFixed(2)}`;
        totalCreditEl.innerText = `${currentSymbol}${totalCredit.toFixed(2)}`;

        // Balance check
        if (totalDebit === totalCredit && totalDebit > 0) {
            balanceStatus.style.display = 'block';
            balanceStatus.style.background = 'rgba(20,184,166,0.1)';
            balanceStatus.innerText = '✓ Balanced';
        } else {
            balanceStatus.style.display = 'block';
            balanceStatus.style.background = 'rgba(224,45,76,0.1)';
            balanceStatus.innerText = `✗ Not Balanced (Diff: ${(totalDebit - totalCredit).toFixed(2)})`;
        }
    }

    // 🔥 Currency change
    currencySelect.addEventListener('change', function () {
        const data = getSelectedCurrencyData();

        currentSymbol = data.symbol;

        // Auto-fill exchange rate
        if (exchangeRateInput) {
            exchangeRateInput.value = data.rate.toFixed(6);
        }

        calculateTotals();
    });

    // 🔥 Real-time typing
    document.addEventListener('input', function (e) {
        if (
            e.target.classList.contains('debit-input') ||
            e.target.classList.contains('credit-input')
        ) {
            calculateTotals();
        }
    });

    // 🔥 Initialize on load
    currencySelect.dispatchEvent(new Event('change'));

// Mobile Menu Toggle
menuToggle.addEventListener("click", function() {
    sidebar.classList.toggle("active");
    overlay.classList.toggle("active");
});

overlay.addEventListener("click", function() {
    sidebar.classList.remove("active");
    overlay.classList.remove("active");
});
});