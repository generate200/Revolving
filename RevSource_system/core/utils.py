import os
import uuid
from django.utils.text import slugify
from decimal import Decimal


def generate_upload_path(instance, filename, folder='uploads'):
    ext = filename.split('.')[-1].lower()
    name = slugify(getattr(instance, 'name', 'item'))
    unique_id = uuid.uuid4().hex[:8]

    filename = f"{name}-{unique_id}.{ext}"
    return os.path.join(folder, filename)


# ✅ IMPORTANT: NO INNER FUNCTION
def product_upload_path(instance, filename):
    return generate_upload_path(instance, filename, 'products/images')

def profile_upload_path(instance, filename):
    return generate_upload_path(instance, filename, 'accounts/profile_pics')


# ==================== CURRENCY CONVERSION UTILITIES ====================

def get_base_currency():
    """Get the system's base currency.
    
    Returns:
        Currency object or None if no base currency is set
    """
    from finance.models import Currency
    return Currency.objects.filter(is_base=True).first()


def convert_to_base_currency(amount, from_currency, exchange_rate_snapshot=None):
    """Convert an amount from any currency to the base currency.
    
    Args:
        amount (Decimal): The amount to convert
        from_currency: Currency instance
        exchange_rate_snapshot (Decimal): Optional historical exchange rate (at transaction time).
                                         If None, uses current rate from from_currency.
                                         
    Returns:
        Decimal: Amount converted to base currency
        
    Formula: 
        To convert FROM any currency TO base currency:
        base_amount = amount / exchange_rate
        where exchange_rate is defined as "units of currency per 1 base currency"
    """
    if not amount:
        return Decimal('0.00')
    
    base_currency = get_base_currency()
    if not base_currency or not from_currency:
        return Decimal(amount)
    
    # If already in base currency, no conversion needed
    if from_currency.id == base_currency.id:
        return Decimal(amount)
    
    # Use provided snapshot rate or current rate
    rate = exchange_rate_snapshot or from_currency.exchange_rate
    
    if not rate or rate == 0:
        return Decimal(amount)
    
    # Convert: amount / rate converts from foreign currency to base currency
    # Example: 80 QAR / 3.64 (where 1 USD = 3.64 QAR) = 21.98 USD
    base_amount = (Decimal(amount) / Decimal(rate)).quantize(Decimal('0.01'))
    return base_amount


def convert_from_base_currency(amount, to_currency, exchange_rate_snapshot=None):
    """Convert an amount from base currency to another currency.
    
    Args:
        amount (Decimal): The base currency amount to convert
        to_currency: Currency instance to convert to
        exchange_rate_snapshot (Decimal): Optional historical exchange rate.
        
    Returns:
        Decimal: Amount converted to target currency
        
    Formula:
        To convert FROM base currency TO any currency:
        target_amount = amount * exchange_rate
        where exchange_rate is defined as "units of currency per 1 base currency"
    """
    if not amount:
        return Decimal('0.00')
    
    base_currency = get_base_currency()
    if not base_currency or not to_currency:
        return Decimal(amount)
    
    # If already in target currency, no conversion needed
    if to_currency.id == base_currency.id:
        return Decimal(amount)
    
    # Use provided snapshot rate or current rate
    rate = exchange_rate_snapshot or to_currency.exchange_rate
    
    if not rate or rate == 0:
        return Decimal(amount)
    
    # Convert: amount * rate converts from base currency to target currency
    # Example: 100 USD * 3.64 (where 1 USD = 3.64 QAR) = 364 QAR
    target_amount = (Decimal(amount) * Decimal(rate)).quantize(Decimal('0.01'))
    return target_amount


def convert_between_currencies(amount, from_currency, to_currency, exchange_rate_snapshot=None):
    """Convert an amount between any two currencies.
    
    Args:
        amount (Decimal): The amount to convert
        from_currency: Source Currency instance
        to_currency: Target Currency instance
        exchange_rate_snapshot (Decimal): Optional historical exchange rate for from_currency.
                                         If provided, uses this rate instead of current.
        
    Returns:
        Decimal: Amount converted to target currency
        
    Formula:
        1. Convert from_currency -> base: amount * from_rate
        2. Convert base -> to_currency: result / to_rate
        3. Combined: (amount * from_rate) / to_rate
    """
    if not amount:
        return Decimal('0.00')
    
    # If same currency, no conversion
    if from_currency.id == to_currency.id:
        return Decimal(amount)
    
    base_currency = get_base_currency()
    if not base_currency:
        return Decimal(amount)
    
    # If from_currency is base, just convert to target
    if from_currency.id == base_currency.id:
        return convert_from_base_currency(amount, to_currency)
    
    # If to_currency is base, just convert from source
    if to_currency.id == base_currency.id:
        return convert_to_base_currency(amount, from_currency, exchange_rate_snapshot)
    
    # General case: convert through base currency
    base_amount = convert_to_base_currency(amount, from_currency, exchange_rate_snapshot)
    target_amount = convert_from_base_currency(base_amount, to_currency)
    
    return target_amount


def get_exchange_rate_for_conversion(from_currency, to_currency):
    """Get the exchange rate between two currencies.
    
    Returns the rate: 1 unit of from_currency = X units of to_currency
    
    Args:
        from_currency: Source Currency instance
        to_currency: Target Currency instance
        
    Returns:
        Decimal: Exchange rate (1 unit of from_currency in to_currency)
    """
    if from_currency.id == to_currency.id:
        return Decimal('1.0')
    
    base_currency = get_base_currency()
    if not base_currency:
        return Decimal('1.0')
    
    from_rate = from_currency.exchange_rate if from_currency.id != base_currency.id else Decimal('1.0')
    to_rate = to_currency.exchange_rate if to_currency.id != base_currency.id else Decimal('1.0')
    
    if not from_rate or from_rate == 0 or not to_rate or to_rate == 0:
        return Decimal('1.0')
    
    # Rate = to_rate / from_rate
    # With rates stored as "units of currency per 1 base currency".
    # Example: 1 USD = 3.64 QAR, 1 USD = 0.85 EUR
    # QAR -> EUR = 0.85 / 3.64
    rate = (Decimal(to_rate) / Decimal(from_rate)).quantize(Decimal('0.0001'))
    return rate