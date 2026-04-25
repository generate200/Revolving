from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from .models import SalesInvoice, StockMovement


@receiver(post_save, sender=SalesInvoice)
def handle_invoice_status_change(sender, instance, created, update_fields, **kwargs):
    """
    Handle stock adjustments when invoice status changes
    - Completed: Stock already reduced in view
    - Refunded: Restore stock (return movement)
    - Cancelled: Restore stock (return movement)
    """
    # Skip if this is a new invoice
    if created:
        return
    
    # Check if status was updated
    if update_fields and 'status' not in update_fields:
        return
    
    # Only process refunded or cancelled invoices
    if instance.status in ['refunded', 'cancelled']:
        # Check if we already created return movements
        existing_returns = StockMovement.objects.filter(
            reference=f'{instance.invoice_number}-return',
            movement_type='return'
        ).count()
        
        if existing_returns > 0:
            return  # Already processed
        
        # Restore stock for each line item
        for line in instance.lines.all():
            # Create return stock movement
            StockMovement.objects.create(
                product=line.product,
                variant=line.variant,
                quantity=line.quantity,  # Positive quantity for return
                movement_type='return',
                reference=f'{instance.invoice_number}-return'
            )
            
            # Restore product stock
            line.product.stock_quantity += float(line.quantity)
            line.product.save(update_fields=['stock_quantity'])
            
            # Restore variant stock if applicable
            if line.variant:
                line.variant.stock_quantity += float(line.quantity)
                line.variant.save(update_fields=['stock_quantity'])
