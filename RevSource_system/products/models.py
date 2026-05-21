from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.utils import product_upload_path
# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=['is_active'], name='category_active_idx'),
            models.Index(fields=['parent'], name='category_parent_idx'),
        ]


class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    contact_person = models.CharField(max_length=255, blank=True)
    Company_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['is_active'], name='supplier_active_idx'),
            models.Index(fields=['email'], name='supplier_email_idx'),
        ]


class Product(models.Model):
    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('kg', 'Kilogram'),
        ('liter', 'Liter'),
        ('meter', 'Meter'),
        ('box', 'Box'),
        ('pack', 'Pack'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sku = models.CharField(max_length=100, unique=True, help_text="Stock Keeping Unit")
    barcode = models.CharField(max_length=100, blank=True,null=True, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.ForeignKey('finance.Currency', on_delete=models.SET_NULL, null=True, blank=True, default=1)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    stock_quantity = models.PositiveIntegerField(default=0)
    reorder_point = models.PositiveIntegerField(default=0, help_text="Minimum stock level before reorder")
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece')
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('0.00'))])
    dimensions = models.CharField(max_length=100, blank=True, help_text="e.g., 10x20x30 cm")
    image = models.ImageField(upload_to=product_upload_path, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    has_variants = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    class Meta:
        indexes = [
            models.Index(fields=['sku'], name='product_sku_idx'),
            models.Index(fields=['is_active'], name='product_active_idx'),
            models.Index(fields=['category'], name='product_category_idx'),
            models.Index(fields=['supplier'], name='product_supplier_idx'),
            models.Index(fields=['stock_quantity'], name='product_stock_idx'),
        ]
    
    @property
    def profit_margin(self):
        if self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return Decimal('0.00')

    @property
    def discounted_price(self):
        if self.discount_percentage > 0:
            discount = (self.selling_price * self.discount_percentage) / 100
            return self.selling_price - discount
        return self.selling_price

    @property
    def discounted_price_base_currency(self):
        """Get the discounted price converted to base currency.
        
        If the product's price is in a non-base currency, convert it to base currency
        using the currency's current exchange rate.
        
        Example:
            - Product price: 100 EUR
            - EUR exchange rate: 1.1 (1 EUR = 1.1 USD)  
            - Base currency: USD
            - Result: 100 * 1.1 = 110 USD
        """
        if not self.currency:
            return self.discounted_price
        
        from core.utils import convert_to_base_currency, get_base_currency
        
        base_currency = get_base_currency()
        if not base_currency or self.currency == base_currency:
            return self.discounted_price
        
        # Convert from product's currency to base currency
        return convert_to_base_currency(
            amount=self.discounted_price,
            from_currency=self.currency
        )
    
    def get_price_in_currency(self, target_currency):
        """Get the discounted price converted to a specific currency.
        
        Args:
            target_currency: Currency instance to convert to
            
        Returns:
            Decimal: Price in target currency
        """
        from core.utils import convert_between_currencies
        
        if not self.currency or not target_currency:
            return self.discounted_price
        
        if self.currency.id == target_currency.id:
            return self.discounted_price
        
        return convert_between_currencies(
            amount=self.discounted_price,
            from_currency=self.currency,
            to_currency=target_currency
        )

    @property
    def is_low_stock(self):
        """Check if available stock is at or below reorder point"""
        return self.available_stock <= self.reorder_point

    @property
    def available_stock(self):
        """Calculate available stock from all movements"""
        from sales.models import StockMovement
        from django.db.models import Sum
        # Sum all movements (already signed: negative for sales, positive for returns)
        total_movements = StockMovement.objects.filter(
            product=self
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Available = Initial stock + all movements
        available = float(self.stock_quantity) + float(total_movements)
        return max(0, int(available))  # Never go below 0

    @property
    def latest_movement_date(self):
        """Return the most recent stock movement timestamp for this product."""
        from sales.models import StockMovement
        return StockMovement.objects.filter(
            product=self
        ).order_by('-created_at').values_list('created_at', flat=True).first()

    class Meta:
        ordering = ['name']


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    attributes = models.JSONField(default=dict)
    sku = models.CharField(max_length=100, unique=True)
    additional_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.name}"

    @property
    def available_stock(self):
        """Calculate available stock from all movements"""
        from sales.models import StockMovement
        from django.db.models import Sum
        
        # Sum all movements (already signed: negative for sales, positive for returns)
        total_movements = StockMovement.objects.filter(
            variant=self
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        # Available = Initial stock + all movements
        available = float(self.stock_quantity) + float(total_movements)
        return max(0, int(available))  # Never go below 0

    class Meta:
        unique_together = ('product', 'attributes')
class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)

