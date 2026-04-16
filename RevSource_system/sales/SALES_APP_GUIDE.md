# Sales & POS System - Setup & Usage Guide

## Overview

The Sales app provides a complete Point-of-Sale (POS) system with a high-speed cart engine for processing transactions. It includes:

- **Cart Interface**: High-speed product addition via barcode scanning, SKU search, or name search
- **Multiple Input Methods**: Barcode scanner support, keyboard shortcuts, text search
- **Currency Support**: Integrated with the finance app's currency utility for multi-currency transactions
- **Invoice Management**: Complete invoice lifecycle from draft to completed
- **Payment Processing**: Support for cash, card, and mobile payments
- **Stock Tracking**: Automatic inventory movement recording
- **Receipt Printing**: Professional receipt format with print-friendly layout

## Models

### 1. **SalesInvoice**
Main invoice model for POS transactions.

Fields:
- `customer`: Customer (optional) - for walk-in customers
- `invoice_number`: Unique invoice identifier (auto-generated)
- `currency`: Selected currency for the transaction
- `subtotal`: Sum of all line items
- `discount_total`: Total discounts applied
- `tax_total`: Total tax amount
- `total_amount`: Final invoice total
- `paid_amount`: Amount paid by customer
- `change_amount`: Change given to customer
- `status`: Draft, Completed, Cancelled, or Refunded
- `created_at`: Timestamp of invoice creation
- `posted_at`: Timestamp of invoice completion

### 2. **SalesLine**
Individual line items in an invoice.

Fields:
- `invoice`: Foreign key to SalesInvoice
- `product`: Foreign key to Product
- `variant`: Optional product variant
- `quantity`: Item quantity (supports decimals)
- `unit_price`: Price per unit
- `discount`: Line-level discount
- `tax`: Line-level tax
- `total_price`: Auto-calculated total

### 3. **Payment**
Payment records for completed invoices.

Fields:
- `invoice`: Foreign key to SalesInvoice
- `method`: Payment method (Cash, Card, Mobile)
- `amount`: Payment amount
- `reference`: Transaction reference (optional)
- `created_at`: Payment timestamp

### 4. **StockMovement**
Tracks inventory changes from sales.

Fields:
- `product`: Foreign key to Product
- `variant`: Optional product variant
- `quantity`: Quantity moved
- `movement_type`: Type of movement (sale, purchase, adjustment, return)
- `reference`: Invoice number or reference
- `created_at`: Timestamp

### 5. **Sale** (Legacy)
Legacy sales tracking model for historical compatibility.

## Features

### High-Speed Cart Engine

**Barcode Scanning Mode**
- Accepts native barcode scanner input (typically USB)
- Auto-detects barcode input patterns
- Searches by barcode, SKU, or product name
- Single-result products are auto-added to cart

**Product Search**
- Real-time product search as you type
- Searches across product name, SKU, and barcode
- Displays matching products with prices
- Click to add to cart

**Quick Add to Cart**
- Single-click product addition
- Quantity editing with auto-calculation
- Real-time total updates
- Delete items from cart

### Currency Management

Integrated with `finance.utils.currency.CurrencyService`:
- Select currency at invoice creation
- Change currency mid-transaction
- Automatic rate conversion
- Exchange rate tracking

### Payment Processing

**Multiple Payment Methods**
- Cash
- Card (with transaction reference)
- Mobile Payment
- Check

**Change Calculation**
- Automatic change calculation
- Visual feedback on overpayment

### Reporting

Access via `/sales/invoices/` to:
- Filter by status
- View detailed invoice information
- Print receipts
- Access payment history

## URL Routes

| URL | Name | Purpose |
|-----|------|---------|
| `/sales/` | pos_dashboard | POS dashboard and quick actions |
| `/sales/invoice/create/` | create_invoice | Create new invoice |
| `/sales/invoice/<id>/cart/` | pos_cart | Main POS cart interface |
| `/sales/invoices/` | invoice_list | View all invoices |
| `/sales/invoice/<id>/` | invoice_detail | View invoice details |
| `/sales/invoice/<id>/print/` | print_receipt | Print receipt |
| `/sales/api/invoice/<id>/add/` | add_to_cart | AJAX: Add product to cart |
| `/sales/api/invoice/<id>/line/<id>/update/` | update_line_item | AJAX: Update line item |
| `/sales/api/invoice/<id>/line/<id>/remove/` | remove_line_item | AJAX: Remove line item |
| `/sales/api/invoice/<id>/payment/` | process_payment | AJAX: Process payment |
| `/sales/api/products/search/` | search_products | AJAX: Search products |

## CSS & JavaScript

### CSS Classes

Key CSS classes for styling:

- `.pos-container`: Main grid layout
- `.cart-panel`: Left panel with cart items
- `.summary-panel`: Right panel with totals and payment
- `.cart-item`: Individual cart item
- `.summary-box`: Summary section with border
- `.payment-section`: Payment method selection

### JavaScript Functions

Key functions in `pos_cart.js`:

- `addProductToCart(product)`: Add product to cart
- `updateLineQuantity(input)`: Update quantity
- `removeLineItem(lineId)`: Remove item
- `processPayment()`: Complete transaction
- `searchProduct(query)`: Search products
- `calculateChange()`: Calculate change amount

## Admin Interface

Access via Django admin (`/admin/`):

- **SalesInvoice Admin**: View/manage invoices with inline line items and payments
- **SalesLine Admin**: View invoice line items
- **Payment Admin**: View payment records
- **StockMovement Admin**: View inventory movements

## Usage Workflow

### Creating a Sale

1. Click "New Invoice" on dashboard
2. Select customer (optional) and currency
3. Set default discount if needed
4. Click "Continue to Cart"
5. Use barcode scanner or search for products
6. Add items (quantity adjusts automatically)
7. Verify total amount
8. Select payment method
9. Enter amount paid
10. Click "Complete Sale"

### Searching for Products

**Methods:**
1. **Barcode Scanning**: Point barcode scanner at product - auto-adds if single result
2. **SKU Search**: Type SKU code in search box
3. **Name Search**: Type product name for fuzzy matching
4. **All Three**: Search works across all fields simultaneously

### Managing Invoices

- **Draft Invoices**: Return to cart to add more items or adjust quantities
- **Completed Invoices**: View details and print receipts
- **Invoice List**: Filter by status to find specific invoices

## Integration with Other Apps

### Products App
- Fetches product information (name, SKU, barcode, price)
- Manages product variants
- Tracks stock through StockMovement

### Finance App
- Currency conversion using CurrencyService
- Exchange rate application
- Multi-currency reporting

### CRM App
- Customer information (name, phone, email)
- Loyalty points tracking
- Credit limit management

### Accounts App
- User authentication
- Staff access control

## API Reference

### Add to Cart
```
POST /sales/api/invoice/{invoice_id}/add/

{
    "product_id": 1,
    "quantity": 5,
    "unit_price": "29.99"
}

Response:
{
    "success": true,
    "line_id": 42,
    "subtotal": "149.95",
    "total": "164.95",
    "cart_count": 3
}
```

### Update Line Item
```
POST /sales/api/invoice/{invoice_id}/line/{line_id}/update/

{
    "quantity": 10,
    "unit_price": "25.00",
    "discount": "5.00",
    "tax": "3.00"
}

Response:
{
    "success": true,
    "total_price": "273.00",
    "subtotal": "300.00",
    "total": "315.00"
}
```

### Remove Line Item
```
DELETE /sales/api/invoice/{invoice_id}/line/{line_id}/

Response:
{
    "success": true,
    "subtotal": "150.00",
    "total": "165.00",
    "cart_count": 2
}
```

### Process Payment
```
POST /sales/api/invoice/{invoice_id}/payment/

{
    "payments": [
        {
            "method": "cash",
            "amount": "170.00",
            "reference": ""
        }
    ]
}

Response:
{
    "success": true,
    "invoice_number": "INV-20260416-00001",
    "total": "165.00",
    "paid": "170.00",
    "change": "5.00"
}
```

### Search Products
```
GET /sales/api/products/search/?q=search_term

Response:
{
    "products": [
        {
            "id": 1,
            "name": "Product Name",
            "sku": "SKU123",
            "barcode": "1234567890",
            "price": "29.99"
        }
    ]
}
```

## Configuration

### Settings (settings.py)

Ensure these apps are in INSTALLED_APPS:
```python
INSTALLED_APPS = [
    'accounts',
    'products',
    'finance',
    'crm',
    'dashboard',
    'sales',
    # Django apps...
]
```

### URL Configuration (urls.py)

Add to main urlpatterns:
```python
path('sales/', include('sales.urls', namespace='sales')),
```

## Keyboard Shortcuts

- **Barcode Scan**: Scanner input + Enter
- **Delete Item**: Click trash icon
- **Focus Search**: CTRL+K (when implemented)

## Troubleshooting

### Products Not Appearing
1. Check product is marked as active
2. Verify product has price set
3. Check search query matches product name/SKU/barcode

### Currency Not Changing
1. Verify currency is marked as active
2. Check exchange_rate is set (not 0)
3. Ensure base currency is selected

### Cart Not Updating
1. Check browser console for JS errors
2. Verify CSRF token is correct
3. Check Django debug logs

### Stock Not Moving
1. Ensure invoice is marked as completed (not draft)
2. Check StockMovement records were created
3. Verify product quantity was calculated correctly

## Future Enhancements

- [ ] Customer loyalty points system
- [ ] Invoice history per customer
- [ ] Discount code system
- [ ] Receipt customization
- [ ] Email receipt delivery
- [ ] Mobile app integration
- [ ] Advanced reporting and analytics
- [ ] Inventory forecasting

## Support

For issues or feature requests, refer to the main project documentation.
