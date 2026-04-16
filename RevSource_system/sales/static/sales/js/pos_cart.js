// POS Cart JavaScript
// Configuration
const config = {
    invoiceId: null,
    totalPrice: null,
    paymentMethods: [],
    csrfToken: '',
    selectedCurrency: ''
};

// Initialize config from template
function initializeConfig(invoiceId, totalPrice, paymentMethods, csrfToken, selectedCurrency) {
    config.invoiceId = invoiceId;
    config.totalPrice = totalPrice;
    
    if (typeof paymentMethods === 'string') {
        try {
            config.paymentMethods = JSON.parse(paymentMethods);
        } catch (err) {
            console.error('Invalid paymentMethods JSON:', err);
            config.paymentMethods = [];
        }
    } else {
        config.paymentMethods = paymentMethods;
    }

    if (!Array.isArray(config.paymentMethods)) {
        config.paymentMethods = [];
    }

    config.csrfToken = csrfToken;
    config.selectedCurrency = selectedCurrency;
}

let cart = {};
let debounceTimer;
let searchTimeout;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    const subtotal= document.getElementById('subtotalDisplay');
    const tax= document.getElementById('taxDisplay');
    const discount= document.getElementById('discountDisplay');
    const total= document.getElementById('totalDisplay');

    if (!subtotal || !tax || !discount || !total) {
        console.error('One or more cart total elements not found on page.');
        return;
    }
    // Initialize cart object after config is set
    cart = {
        invoiceId: config.invoiceId,
        subtotal: parseFloat(document.getElementById('subtotalDisplay').textContent),
        tax: parseFloat(document.getElementById('taxDisplay').textContent),
        discount: parseFloat(document.getElementById('discountDisplay').textContent),
        total: parseFloat(document.getElementById('totalDisplay').textContent),
    };
    
    initializePaymentMethods();
    initializeEventListeners();
    enableBarcodeMode();
});

/**
 * Initialize payment method buttons
 */
function initializePaymentMethods() {
    const methodsDiv = document.getElementById('paymentMethods');
    methodsDiv.innerHTML = '';

    if (!Array.isArray(config.paymentMethods) || config.paymentMethods.length === 0) {
        methodsDiv.innerHTML = '<div class="text-muted">No payment methods available.</div>';
        return;
    }

    config.paymentMethods.forEach(methodPair => {
        const [value, label] = methodPair;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-outline-primary payment-method-btn';
        btn.dataset.method = value;
        btn.textContent = label;
        btn.onclick = () => selectPaymentMethod(value);
        methodsDiv.appendChild(btn);
    });
}

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
    // Product search
    const productSearchInput = document.getElementById('productSearch');
    if (productSearchInput) {
        productSearchInput.addEventListener('input', debounceSearch);
    } else {
        console.warn('Product search input not found on page.');
    }
    
    // Quantity changes
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('quantity-input')) {
            updateLineQuantity(e.target);
        }
    });

    // Remove buttons
    document.addEventListener('click', function(e) {
        if (e.target.closest('.remove-line')) {
            const btn = e.target.closest('.remove-line');
            removeLineItem(btn.dataset.lineId);
        }
    });

    // Payment amount change
    document.getElementById('amountPaid').addEventListener('input', calculateChange);
    
    // Complete payment button
    document.getElementById('completePayment').addEventListener('click', processPayment);
    
    // Hold invoice button
    document.getElementById('holdInvoice').addEventListener('click', holdInvoice);
}

/**
 * Enable barcode scanning mode
 */
function enableBarcodeMode() {
    const barcodeInput = document.getElementById('productSearch');
    let barcodeBuffer = '';
    let barcodeTimeout;

    document.addEventListener('keydown', function(e) {
        // Typical barcode scanner sends quickly with Enter key at the end
        if (e.key === 'Enter' && barcodeBuffer.length > 0) {
            e.preventDefault();
            searchProduct(barcodeBuffer);
            barcodeBuffer = '';
            clearTimeout(barcodeTimeout);
            return;
        }

        // Accumulate barcode characters
        if (e.key.match(/^[a-zA-Z0-9]$/)) {
            barcodeBuffer += e.key;
            clearTimeout(barcodeTimeout);
            
            document.getElementById('barcodeMode').classList.add('active');
            
            // Reset buffer after 500ms of inactivity
            barcodeTimeout = setTimeout(() => {
                barcodeBuffer = '';
                document.getElementById('barcodeMode').classList.remove('active');
            }, 500);
        }
    });
}

/**
 * Debounce search input
 */
function debounceSearch(e) {
    clearTimeout(searchTimeout);
    const query = e.target.value.trim();

    if (query.length < 2) {
        document.getElementById('searchResults').style.display = 'none';
        return;
    }

    searchTimeout = setTimeout(() => {
        performSearch(query);
    }, 300);
}

/**
 * Perform product search
 */
function performSearch(query) {
    fetch(`/sales/api/products/search/?q=${encodeURIComponent(query)}`)
        .then(r => {
            if (!r.ok) {
                throw new Error(`Search request failed: ${r.status} ${r.statusText}`);
            }
            return r.json();
        })
        .then(data => {
            if (!data || !Array.isArray(data.products)) {
                console.warn('Search response did not contain products array:', data);
                displaySearchResults([]);
                return;
            }
            displaySearchResults(data.products);
        })
        .catch(err => {
            console.error('Search error:', err);
            displaySearchResults([]);
        });
}

/**
 * Search product by barcode/SKU directly
 */
function searchProduct(query) {
    fetch(`/sales/api/products/search/?q=${encodeURIComponent(query)}`)
        .then(r => {
            if (!r.ok) {
                throw new Error(`Search request failed: ${r.status} ${r.statusText}`);
            }
            return r.json();
        })
        .then(data => {
            if (!data || !Array.isArray(data.products)) {
                console.warn('Search response invalid for direct search:', data);
                showAlert('Product search failed', 'warning');
                return;
            }

            if (data.products.length === 1) {
                // Auto-add if single result
                addProductToCart(data.products[0]);
            } else if (data.products.length > 1) {
                displaySearchResults(data.products);
            } else {
                displaySearchResults([]);
            }
        })
        .catch(err => {
            console.error('Search error:', err);
            showAlert('Search error', 'danger');
        });
}

/**
 * Display search results
 */
function displaySearchResults(products) {
    const resultsList = document.getElementById('productsList');
    if (!resultsList) {
        console.error('Products list container not found.');
        return;
    }

    resultsList.innerHTML = '';

    if (!Array.isArray(products) || products.length === 0) {
        resultsList.innerHTML = '<div class="list-group-item disabled">No products found</div>';
        const searchResults = document.getElementById('searchResults');
        if (searchResults) {
            searchResults.style.display = 'block';
        }
        return;
    }

    products.forEach(product => {
        const item = document.createElement('button');
        item.type = 'button';
        item.className = 'list-group-item list-group-item-action';
        item.innerHTML = `
            <div style="display: flex; justify-content: space-between;">
                <div>
                    <strong>${product.name}</strong><br>
                    <small class="text-muted">SKU: ${product.sku}${product.barcode ? ` | Barcode: ${product.barcode}` : ''}</small>
                </div>
                <div style="text-align: right;">
                    <strong>$${parseFloat(product.price).toFixed(2)}</strong>
                </div>
            </div>
        `;
        item.onclick = () => addProductToCart(product);
        resultsList.appendChild(item);
    });

    document.getElementById('searchResults').style.display = 'block';
}

/**
 * Add product to cart
 */
function addProductToCart(product) {
    const payload = {
        product_id: product.id,
        quantity: 1,
        unit_price: product.price
    };

    fetch(`/sales/api/invoice/${cart.invoiceId}/add/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': config.csrfToken
        },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            refreshCart();
            document.getElementById('productSearch').value = '';
            document.getElementById('searchResults').style.display = 'none';
            showAlert(`Added ${product.name}`, 'success');
        } else {
            showAlert(data.error || 'Error adding product', 'danger');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        showAlert('Error adding product', 'danger');
    });
}

/**
 * Update line item quantity
 */
function updateLineQuantity(input) {
    clearTimeout(debounceTimer);
    
    debounceTimer = setTimeout(() => {
        const lineId = input.dataset.lineId;
        const quantity = parseFloat(input.value);

        if (quantity <= 0) {
            removeLineItem(lineId);
            return;
        }

        const payload = { quantity: quantity };

        fetch(`/sales/api/invoice/${cart.invoiceId}/line/${lineId}/update/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': config.csrfToken
            },
            body: JSON.stringify(payload)
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                updateTotals(data);
            } else {
                showAlert(data.error || 'Error updating cart', 'danger');
            }
        })
        .catch(err => console.error('Update error:', err));
    }, 500);
}

/**
 * Remove line item from cart
 */
function removeLineItem(lineId) {
    if (!confirm('Remove this item from cart?')) return;

    fetch(`/sales/api/invoice/${cart.invoiceId}/line/${lineId}/remove/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': config.csrfToken
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            refreshCart();
            showAlert('Item removed', 'info');
        } else {
            showAlert(data.error || 'Error removing item', 'danger');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        showAlert('Error removing item', 'danger');
    });
}

/**
 * Update cart display after changes
 */
function updateTotals(data) {
    document.getElementById('subtotalDisplay').textContent = 
        parseFloat(data.subtotal).toFixed(2);
    document.getElementById('totalDisplay').textContent = 
        parseFloat(data.total).toFixed(2);
    
    cart.subtotal = parseFloat(data.subtotal);
    cart.total = parseFloat(data.total);
    
    document.getElementById('paymentAmount').value = cart.total.toFixed(2);
    calculateChange();
}

/**
 * Refresh cart from server
 */
function refreshCart() {
    location.reload();
}

/**
 * Select payment method
 */
function selectPaymentMethod(method) {
    const buttons = document.querySelectorAll('.payment-method-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    event.target.classList.add('active');
    document.getElementById('amountPaid').focus();
}

/**
 * Calculate change
 */
function calculateChange() {
    const amountPaid = parseFloat(document.getElementById('amountPaid').value) || 0;
    const total = parseFloat(document.getElementById('totalDisplay').textContent);
    const change = amountPaid - total;

    document.getElementById('changeDisplay').textContent = 
        change.toFixed(2);
    
    // Enable payment button if amount is sufficient
    const completeBtn = document.getElementById('completePayment');
    completeBtn.disabled = amountPaid < total;
}

/**
 * Process payment and complete transaction
 */
function processPayment() {
    const amountPaid = parseFloat(document.getElementById('amountPaid').value);
    const total = parseFloat(document.getElementById('totalDisplay').textContent);
    const methodBtn = document.querySelector('.payment-method-btn.active');

    if (!methodBtn) {
        showAlert('Please select a payment method', 'warning');
        return;
    }

    if (amountPaid < total) {
        showAlert('Insufficient payment amount', 'warning');
        return;
    }

    const payload = {
        payments: [{
            method: methodBtn.textContent.toLowerCase().split(' ')[0],
            amount: amountPaid,
            reference: document.getElementById('referenceInput')?.value || ''
        }]
    };

    document.getElementById('completePayment').disabled = true;

    fetch(`/sales/api/invoice/${cart.invoiceId}/payment/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': config.csrfToken
        },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showAlert('Sale completed successfully!', 'success');
            setTimeout(() => {
                window.location.href = `/sales/invoice/${cart.invoiceId}/`;
            }, 1500);
        } else {
            document.getElementById('completePayment').disabled = false;
            showAlert(data.error || 'Error processing payment', 'danger');
        }
    })
    .catch(err => {
        document.getElementById('completePayment').disabled = false;
        console.error('Payment error:', err);
        showAlert('Error processing payment', 'danger');
    });
}

/**
 * Hold invoice (save as draft)
 */
function holdInvoice() {
    showAlert('Invoice saved for later. You can access it from the invoice list.', 'info');
    setTimeout(() => {
        window.location.href = '/sales/';
    }, 1500);
}

/**
 * Show alert toast
 */
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        min-width: 300px;
        z-index: 1000;
    `;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 4000);
}

/**
 * Change currency
 */
function changeCurrency() {
    const curr = document.getElementById('currencySelect').value;
    window.location.href = `?currency=${curr}`;
}
