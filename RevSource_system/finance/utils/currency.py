from decimal import Decimal
from finance.models import Currency
class CurrencyService:
    def __init__(self, request):
        self.request = request
        self.selected_currency = self.get_selected_currency()
        self.base_currency = Currency.objects.filter(is_base=True).first()

    def get_selected_currency(self):
        code = self.request.GET.get('currency')

        if code:
            currency = Currency.objects.filter(code=code, is_active=True).first()
            if currency:
                return currency

        return Currency.objects.filter(is_base=True).first()

    def convert(self, amount):
        if not amount:
            return Decimal('0.00')

        if not self.base_currency or self.base_currency.exchange_rate == 0:
            return amount

        rate = (
            self.selected_currency.exchange_rate /
            self.base_currency.exchange_rate
        )

        return (amount * rate).quantize(Decimal('0.01'))

    def symbol(self):
        return self.selected_currency.symbol

    def context(self):
        return {
            "selected_currency": self.selected_currency,
            "base_currency": self.base_currency,
            "currency_symbol": self.symbol(),
            "currencies": Currency.objects.filter(is_active=True),
        }