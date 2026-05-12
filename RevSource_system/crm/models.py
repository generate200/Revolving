from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator
# Create your models here.
class Customer(models.Model):
    CUSTOMER_TYPES = [
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('vip', 'VIP'),
    ]

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    email = models.EmailField(blank=True, null=True)

    address = models.TextField(blank=True)

    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='retail')

    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    loyalty_points = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=['email'], name='customer_email_idx'),
            models.Index(fields=['customer_type'], name='customer_type_idx'),
            models.Index(fields=['is_active'], name='customer_active_idx'),
            models.Index(fields=['current_balance'], name='customer_balance_idx'),
        ]