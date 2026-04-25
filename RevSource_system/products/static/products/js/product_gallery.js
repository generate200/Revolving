// Product Gallery View Toggle and Modal Management
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const listViewBtn = document.getElementById('list-view-btn');
    const galleryViewBtn = document.getElementById('gallery-view-btn');
    const listViewContainer = document.getElementById('list-view-container');
    const galleryViewContainer = document.getElementById('gallery-view-container');
    const productModal = document.getElementById('product-modal');
    const modalClose = document.getElementById('modal-close');
    const modalBody = document.getElementById('modal-body');

    // Get all product cards/rows for product data
    const productCards = document.querySelectorAll('.gallery-card, .product-row');

    // Store products data from DOM
    let productsData = {};
    
    // Extract product data from the page
    function extractProductData() {
        // From gallery cards
        document.querySelectorAll('.gallery-card').forEach(card => {
            const productId = card.getAttribute('data-product-id');
            const editUrl = card.getAttribute('data-edit-url');
            const deleteUrl = card.getAttribute('data-delete-url');
            const name = card.querySelector('.product-name')?.textContent || 'N/A';
            const sku = card.querySelector('.product-sku')?.textContent?.replace('SKU: ', '') || 'N/A';
            const price = card.querySelector('.product-price')?.textContent || 'N/A';
            const image = card.querySelector('.product-img')?.src || null;
            const stock = card.querySelector('.stock-value')?.textContent || '0';
            const category = document.querySelector(`tr[data-product-id="${productId}"] td:nth-child(3)`)?.textContent || 'N/A';
            const description = ''; // Could be extracted from additional attributes if needed
            const statusBadge = card.querySelector('.badge-success') ? 'Active' : 'Inactive';
            
            productsData[productId] = {
                id: productId,
                name: name,
                sku: sku,
                price: price,
                stock: stock,
                category: category,
                image: image,
                description: description,
                status: statusBadge,
                editUrl: editUrl,
                deleteUrl: deleteUrl
            };
        });
    }

    // Toggle between List and Gallery Views
    listViewBtn.addEventListener('click', function() {
        listViewBtn.classList.add('active');
        galleryViewBtn.classList.remove('active');
        listViewContainer.style.display = 'block';
        galleryViewContainer.style.display = 'none';
    });

    galleryViewBtn.addEventListener('click', function() {
        galleryViewBtn.classList.add('active');
        listViewBtn.classList.remove('active');
        listViewContainer.style.display = 'none';
        galleryViewContainer.style.display = 'block';
    });

    // Open modal with product details
    function openProductModal(productId) {
        const product = productsData[productId];
        if (!product) return;

        const modalHTML = `
            <div class="product-details">
                <div class="product-details-image">
                    ${product.image ? 
                        `<img src="${product.image}" alt="${product.name}">` : 
                        `<div class="placeholder-image"><i class="fas fa-image"></i></div>`
                    }
                </div>
                <div class="product-details-content">
                    <h1 class="details-title">${product.name}</h1>
                    
                    <div class="details-meta">
                        <div class="meta-row">
                            <span class="meta-label">SKU</span>
                            <span class="meta-value">${product.sku}</span>
                        </div>
                        <div class="meta-row">
                            <span class="meta-label">Price</span>
                            <span class="meta-value">${product.price}</span>
                        </div>
                        <div class="meta-row">
                            <span class="meta-label">Stock</span>
                            <span class="meta-value">${product.stock} units</span>
                        </div>
                        <div class="meta-row">
                            <span class="meta-label">Category</span>
                            <span class="meta-value">${product.category}</span>
                        </div>
                    </div>

                    <div class="details-badges">
                        <span class="badge ${product.status === 'Active' ? 'badge-success' : 'badge-muted'}">
                            ${product.status}
                        </span>
                    </div>

                    <div class="details-actions">
                        <a href="${product.editUrl}" class="btn-primary">
                            <i class="fas fa-edit"></i> Edit Product
                        </a>
                        <a href="${product.deleteUrl}" class="btn-secondary" onclick="return confirm('Are you sure you want to delete this product?');">
                            <i class="fas fa-trash"></i> Delete
                        </a>
                    </div>
                </div>
            </div>
        `;

        modalBody.innerHTML = modalHTML;
        productModal.classList.add('active');
    }

    // Close modal
    function closeProductModal() {
        productModal.classList.remove('active');
        modalBody.innerHTML = '';
    }

    // Event Listeners for opening modal
    // From gallery cards
    document.addEventListener('click', function(e) {
        // View Details Button in Gallery
        if (e.target.closest('.view-details-btn')) {
            const productId = e.target.closest('.view-details-btn').getAttribute('data-product-id');
            openProductModal(productId);
            e.preventDefault();
        }
        
        // Product link in List View
        if (e.target.closest('.product-link')) {
            const productId = e.target.closest('.product-link').getAttribute('data-product-id');
            openProductModal(productId);
            e.preventDefault();
        }
    });

    // Close modal on close button
    modalClose.addEventListener('click', closeProductModal);

    // Close modal on background click
    productModal.addEventListener('click', function(e) {
        if (e.target === productModal) {
            closeProductModal();
        }
    });

    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && productModal.classList.contains('active')) {
            closeProductModal();
        }
    });
    document.querySelectorAll('.product-row').forEach(row => {

    row.addEventListener('dblclick', function(e) {

        // prevent double-click on delete/actions from redirecting
        if (e.target.closest('.btn-outline, a[href]')) {
            return;
        }

        window.location = this.dataset.href;
    });

});

    // Initialize
    extractProductData();
    console.log('Product Gallery loaded successfully');
});
