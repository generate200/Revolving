from finance.models import Currency

def currency_context(request):
    """
    Context processor to make currency data available globally
    """
    currencies = Currency.objects.filter(is_active=True)
    base_currency = currencies.filter(is_base=True).first()

    return {
        'currencies': currencies,
        'base_currency': base_currency.code if base_currency else 'USD',
    }