from decimal import Decimal
from finance.models import Currency
from core.utils import (
    convert_between_currencies,
    convert_to_base_currency,
    convert_from_base_currency,
    get_exchange_rate_for_conversion,
    get_base_currency
)


class CurrencyService:
    """Service for handling multi-currency operations.
    
    This service allows conversion between any currencies, not just to/from base.
    It can work with any base currency, not just USD.
    """
    
    def __init__(self, request=None, base_currency=None, selected_currency=None):
        """Initialize the currency service.
        
        Args:
            request: Optional Django request object (for getting query params)
            base_currency: Optional Currency instance to use as base. 
                          If None, uses system's configured base currency.
            selected_currency: Optional Currency instance. 
                             If None, uses base currency or request param.
        """
        self.request = request
        self.base_currency = base_currency or get_base_currency()
        
        # Determine selected currency
        if selected_currency:
            self.selected_currency = selected_currency
        elif request:
            self.selected_currency = self.get_selected_currency()
        else:
            self.selected_currency = self.base_currency

    def get_selected_currency(self):
        """Get the currency from request query parameter or default to base."""
        if not self.request:
            return self.base_currency
        
        code = self.request.GET.get('currency')
        if code:
            currency = Currency.objects.filter(code=code, is_active=True).first()
            if currency:
                return currency

        return self.base_currency

    def convert(self, amount, from_currency=None, to_currency=None):
        """Convert an amount between currencies.
        
        Args:
            amount (Decimal): Amount to convert
            from_currency: Source Currency instance. 
                          If None, assumes base currency.
            to_currency: Target Currency instance. 
                        If None, uses selected_currency.
        
        Returns:
            Decimal: Converted amount
        """
        if not amount:
            return Decimal('0.00')
        
        source = from_currency or self.base_currency
        target = to_currency or self.selected_currency
        
        if not source or not target:
            return Decimal(amount).quantize(Decimal('0.01'))
        
        return convert_between_currencies(
            amount=amount,
            from_currency=source,
            to_currency=target
        )
    
    def convert_to_base(self, amount, from_currency):
        """Convert an amount to base currency.
        
        Args:
            amount (Decimal): Amount in from_currency
            from_currency: Source Currency instance
            
        Returns:
            Decimal: Amount in base currency
        """
        if not amount:
            return Decimal('0.00')
        
        if not from_currency or not self.base_currency:
            return Decimal(amount).quantize(Decimal('0.01'))
        
        return convert_to_base_currency(
            amount=amount,
            from_currency=from_currency
        )
    
    def convert_from_base(self, amount, to_currency):
        """Convert an amount from base currency to another currency.
        
        Args:
            amount (Decimal): Amount in base currency
            to_currency: Target Currency instance
            
        Returns:
            Decimal: Amount converted to to_currency
        """
        if not amount:
            return Decimal('0.00')
        
        if not to_currency or not self.base_currency:
            return Decimal(amount).quantize(Decimal('0.01'))
        
        return convert_from_base_currency(
            amount=amount,
            to_currency=to_currency
        )
    
    def get_exchange_rate(self, from_currency=None, to_currency=None):
        """Get the exchange rate between two currencies.
        
        Args:
            from_currency: Source Currency instance. If None, uses base currency.
            to_currency: Target Currency instance. If None, uses selected currency.
            
        Returns:
            Decimal: Exchange rate (1 unit of from = X units of to)
        """
        source = from_currency or self.base_currency
        target = to_currency or self.selected_currency
        
        if not source or not target:
            return Decimal('1.0')
        
        return get_exchange_rate_for_conversion(source, target)

    def symbol(self, currency=None):
        """Get the currency symbol.
        
        Args:
            currency: Currency instance. If None, uses selected_currency.
            
        Returns:
            str: Currency symbol
        """
        target = currency or self.selected_currency
        return target.symbol if target else '$'

    def context(self, currency=None):
        """Get context dictionary for rendering in templates.
        
        Args:
            currency: Specific currency to focus on. If None, uses selected_currency.
            
        Returns:
            dict: Context data for templates
        """
        return {
            "selected_currency": currency or self.selected_currency,
            "base_currency": self.base_currency,
            "currency_symbol": self.symbol(currency),
            "currencies": Currency.objects.filter(is_active=True),
        }
    
    def set_base_currency(self, currency):
        """Change the base currency of the system.
        
        CAUTION: This is a system-wide change that will affect all conversions.
        Only one currency can be marked as base at a time.
        
        Args:
            currency: Currency instance to set as base
        """
        # Unset current base
        Currency.objects.filter(is_base=True).update(is_base=False)
        # Set new base
        currency.is_base = True
        currency.save()
        self.base_currency = currency