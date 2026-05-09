document.addEventListener('DOMContentLoaded', function () {

    // Currency selector table
    const selector = document.getElementById('currency-selector-table');

    // Mobile menu
    const menuToggle = document.getElementById("menuToggle");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");

    // Currency form fields
    const currencySelect = document.getElementById('id_currency');
    const exchangeRateInput = document.getElementById('id_exchange_rate');

    // Totals
    const totalDebitEl = document.getElementById('total-debit');
    const totalCreditEl = document.getElementById('total-credit');
    const balanceStatus = document.getElementById('balance-status');

    // =========================
    // Currency table selector
    // =========================
    if (selector) {
        const urlParams = new URLSearchParams(window.location.search);
        const currencyFromUrl = urlParams.get('currency');

        if (currencyFromUrl) {
            selector.value = currencyFromUrl;
        }

        selector.addEventListener('change', function () {
            const currency = this.value;
            const url = new URL(window.location.href);

            url.searchParams.set('currency', currency);
            window.location.href = url.toString();
        });
    }

    // Prevent JS crash if totals area missing
    if (!totalDebitEl || !totalCreditEl || !balanceStatus) {
        return;
    }

    // =========================
    // Helper Functions
    // =========================
    function round2(value) {
        return Math.round(value * 100) / 100;
    }

    function getSelectedCurrencyData() {
        const selectedOption = currencySelect.options[currencySelect.selectedIndex];

        return {
            symbol: selectedOption.dataset.symbol || '',
            rate: parseFloat(selectedOption.dataset.rate) || 1
        };
    }

    // =========================
    // Totals Calculation
    // =========================
    function calculateTotals() {

        let totalDebit = 0;
        let totalCredit = 0;

        document.querySelectorAll('.debit-input').forEach(input => {
            totalDebit += parseFloat(input.value) || 0;
        });

        document.querySelectorAll('.credit-input').forEach(input => {
            totalCredit += parseFloat(input.value) || 0;
        });

        totalDebitEl.innerText = totalDebit.toFixed(2);
        totalCreditEl.innerText = totalCredit.toFixed(2);

        const difference = round2(totalDebit - totalCredit);

        balanceStatus.style.display = 'block';

        // Balanced
        if (difference === 0 && totalDebit > 0) {

            balanceStatus.style.background = 'rgba(20,184,166,0.1)';
            balanceStatus.style.color = '#14b8a6';
            balanceStatus.innerText = '✓ Balanced';

        } else {

            balanceStatus.style.background = 'rgba(224,45,76,0.1)';
            balanceStatus.style.color = '#E02D4C';

            balanceStatus.innerText =
                `✗ Not Balanced (Diff: ${difference.toFixed(2)})`;
        }
    }

    // =========================
    // Currency Change
    // =========================
    if (currencySelect) {

        currencySelect.addEventListener('change', function () {

            const data = getSelectedCurrencyData();

            if (exchangeRateInput) {
                exchangeRateInput.value = data.rate.toFixed(6);
            }

            calculateTotals();
        });

        // Trigger initial load
        currencySelect.dispatchEvent(new Event('change'));
    }

    // =========================
    // Live Input Tracking
    // =========================
    document.addEventListener('input', function (e) {

        if (
            e.target.classList.contains('debit-input') ||
            e.target.classList.contains('credit-input')
        ) {
            calculateTotals();
        }
    });

    // =========================
    // Mobile Menu
    // =========================
    if (menuToggle && sidebar && overlay) {

        menuToggle.addEventListener("click", function () {
            sidebar.classList.toggle("active");
            overlay.classList.toggle("active");
        });

        overlay.addEventListener("click", function () {
            sidebar.classList.remove("active");
            overlay.classList.remove("active");
        });
    }

});