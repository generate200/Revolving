from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from products.models import Product, ProductVariant
from crm.models import Customer
from finance.models import Currency


class Sale(models.Model):
    """Legacy Sales model - tracks individual product sales"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales_records')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale: {self.product.name} x {self.quantity}"

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date'], name='sale_date_idx'),
        ]


class SalesInvoice(models.Model):
    """Main invoice model for POS transactions"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True, related_name='sales_invoices')
    invoice_number = models.CharField(max_length=50, unique=True)
    
    # Currency tracking
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default=1)

    # Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Payment
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    posted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.invoice_number

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invoice_number'], name='salesinvoice_number_idx'),
            models.Index(fields=['customer'], name='salesinvoice_customer_idx'),
            models.Index(fields=['status'], name='salesinvoice_status_idx'),
            models.Index(fields=['created_at'], name='salesinvoice_created_at_idx'),
            models.Index(fields=['total_amount'], name='salesinvoice_total_idx'),
        ]

    def calculate_totals(self):
        """Recalculate totals from line items"""
        lines = self.lines.all()
        self.subtotal = sum(line.total_price for line in lines)
        self.tax_total = sum(line.tax for line in lines)
        self.total_amount = self.subtotal + self.tax_total - self.discount_total
        self.save()


class SalesLine(models.Model):
    """Individual line item in an invoice"""
    invoice = models.ForeignKey(SalesInvoice, related_name='lines', on_delete=models.CASCADE)
    
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, null=True, blank=True)

    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['product'], name='salesline_product_idx'),
            models.Index(fields=['total_price'], name='salesline_total_price_idx'),
        ]

    def save(self, *args, **kwargs):
        """Auto-calculate total price"""
        self.total_price = (self.quantity * self.unit_price) - self.discount + self.tax
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Payment records for invoices"""
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile', 'Mobile Payment'),
        ('check', 'Check'),
    ]

    invoice = models.ForeignKey(SalesInvoice, related_name='payments', on_delete=models.CASCADE)
    
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    reference = models.CharField(max_length=100, blank=True, help_text="e.g., card txn ID, check number")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_method_display()} - {self.amount}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['method'], name='payment_method_idx'),
            models.Index(fields=['amount'], name='payment_amount_idx'),
        ]


class StockMovement(models.Model):
    """Track inventory changes from sales and other movements"""
    MOVEMENT_TYPES = [
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.CASCADE)

    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)

    reference = models.CharField(max_length=100, help_text="invoice number or reference")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} x {self.quantity}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['movement_type'], name='stock_movement_type_idx'),
            models.Index(fields=['created_at'], name='stock_movement_date_idx'),
            models.Index(fields=['product'], name='stock_movement_product_idx'),
        ]
