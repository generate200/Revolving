# Currency System - Quick Reference

## Your Requirement: Change Base Currency to QAR

### Step 1: Set QAR as Base Currency

```python
from finance.models import Currency
from finance.utils.currency import CurrencyService

# Find QAR in database
qar = Currency.objects.get(code='QAR')

# Set it as base
service = CurrencyService()
service.set_base_currency(qar)

# Verify
base = Currency.objects.filter(is_base=True).first()
print(f"Base currency is now: {base.code}")  # Should print "QAR"
```

### Step 2: All Conversions Now Use QAR as Base

**Before (USD was base):**
```
100 EUR → multiply by 1.1 → 110 USD
```

**After (QAR is base):**
```
100 EUR → multiply by 1.1 → 110 QAR  ✓
```

### Step 3: Update Accounts to Track Their Currency (Optional)

```python
from finance.models import Account, Currency

usd = Currency.objects.get(code='USD')
eur = Currency.objects.get(code='EUR')
qar = Currency.objects.get(code='QAR')

# Mark accounts by their currency
for account in Account.objects.all():
    if account.code.startswith('USD'):
        account.currency = usd
    elif account.code.startswith('EUR'):
        account.currency = eur
    else:
        account.currency = qar  # or leave NULL for base
    account.save()
```

---

## Common Conversions

### Convert from Any Currency to Base (QAR)

```python
from core.utils import convert_to_base_currency
from finance.models import Currency

usd = Currency.objects.get(code='USD')
eur = Currency.objects.get(code='EUR')

# 100 USD → QAR
qar_amount = convert_to_base_currency(100, usd)

# 100 EUR → QAR  
qar_amount = convert_to_base_currency(100, eur)
```

### Convert from Base (QAR) to Any Currency

```python
from core.utils import convert_from_base_currency
from finance.models import Currency

usd = Currency.objects.get(code='USD')

# 1100 QAR → USD
usd_amount = convert_from_base_currency(1100, usd)
```

### Convert Between Non-Base Currencies

```python
from core.utils import convert_between_currencies
from finance.models import Currency

usd = Currency.objects.get(code='USD')
eur = Currency.objects.get(code='EUR')

# 100 USD → EUR
eur_amount = convert_between_currencies(100, usd, eur)
```

### Using CurrencyService (For Web Requests)

```python
from finance.utils.currency import CurrencyService
from finance.models import Currency

qar = Currency.objects.get(code='QAR')
eur = Currency.objects.get(code='EUR')

service = CurrencyService(request, base_currency=qar)

# Simple conversion
price_in_selected = service.convert(100, from_currency=usd)

# Get exchange rate
rate = service.exchange_rate_for_conversion(usd, eur)  # USD to EUR rate
```

---

## Account Operations

### Get Account Balance in Specific Currency

```python
from finance.models import Account, Currency

account = Account.objects.get(code='1000')
eur = Currency.objects.get(code='EUR')
usd = Currency.objects.get(code='USD')

# Get balance in EUR (converts from account's currency)
balance_eur = account.get_balance_in_currency(eur)

# Get balance in base currency (QAR)
balance_qar = account.get_balance_in_base_currency()

# Direct access (in account's currency)
balance_native = account.balance
```

---

## Product Operations

### Product Pricing in Different Currencies

```python
from products.models import Product
from finance.models import Currency

product = Product.objects.get(sku='PROD001')
eur = Currency.objects.get(code='EUR')
qar = Currency.objects.get(code='QAR')

# Price in base currency (QAR)
price_qar = product.discounted_price_base_currency

# Price in any currency
price_eur = product.get_price_in_currency(eur)

# Get price in products currency
price_native = product.discounted_price
```

---

## Journal Entry Operations

### Creating a Multi-Currency Journal Entry

```python
from finance.models import JournalEntry, Account, Currency
from decimal import Decimal
import datetime

# Create entry in EUR, capturing rate from transaction date
entry = JournalEntry.objects.create(
    date=datetime.date(2024, 5, 10),
    description='International Purchase',
    currency=Currency.objects.get(code='EUR'),
    exchange_rate=Decimal('1.15'),  # Rate on 2024-05-10
    entry_type='normal'
)

# Add lines (amounts are in EUR)
cash_usd = Account.objects.get(code='1010')  # USD cash
expense_eur = Account.objects.get(code='5100')  # EUR expense

entry.add_line(cash_usd, credit=1150)  # 1000 EUR converted to USD
entry.add_line(expense_eur, debit=1000)  # 1000 EUR in expense

# Post - automatically handles currency conversions
entry.post()

# Result:
# - cash_usd balance: decreased by 1150 USD
# - expense_eur balance: increased by 1000 EUR
```

### Getting Converted Amounts from Journal Lines

```python
entry = JournalEntry.objects.get(id=123)

for line in entry.lines.all():
    # Amount in entry's currency (EUR)
    native_amount = line.debit or line.credit
    
    # Amount converted to base currency (QAR) 
    qar_amount = line.get_debit_base() or line.get_credit_base()
    
    print(f"{native_amount} EUR = {qar_amount} QAR")
```

---

## Reports & Queries

### Total Assets in Base Currency

```python
from finance.models import Account, Currency
from core.utils import convert_to_base_currency
from decimal import Decimal

total_qar = Decimal('0')
base = Currency.objects.filter(is_base=True).first()

for account in Account.objects.filter(type='asset'):
    balance_qar = account.get_balance_in_base_currency()
    total_qar += balance_qar

print(f"Total Assets: {total_qar} {base.code}")
```

### Total Assets by Currency

```python
from finance.models import Account
from decimal import Decimal

totals = {}

for account in Account.objects.filter(type='asset'):
    currency = account.currency or get_base_currency()
    currency_code = currency.code if currency else 'BASE'
    
    if currency_code not in totals:
        totals[currency_code] = Decimal('0')
    
    totals[currency_code] += account.balance

for currency_code, total in totals.items():
    print(f"{currency_code}: {total}")
```

### Balance Sheet in Multiple Currencies

```python
from finance.models import Account, Currency
from core.utils import convert_to_base_currency
import json

def get_balance_sheet(currencies):
    """Get balance sheet converted to multiple currencies"""
    report = {}
    
    for currency in currencies:
        report[currency.code] = {}
        
        for account_type in ['asset', 'liability', 'equity']:
            total = sum(
                account.get_balance_in_currency(currency)
                for account in Account.objects.filter(type=account_type)
            )
            report[currency.code][account_type] = total
    
    return report

# Get balance sheet in USD, EUR, QAR
currencies = Currency.objects.filter(code__in=['USD', 'EUR', 'QAR'])
sheet = get_balance_sheet(currencies)

print(json.dumps(sheet, indent=2, default=str))
```

---

## Exchange Rate Management

### Updating Exchange Rates

```python
from finance.models import Currency
from decimal import Decimal

# Update EUR rate (1 EUR = 1.12 QAR)
eur = Currency.objects.get(code='EUR')
eur.exchange_rate = Decimal('1.12')
eur.save()

# New rate takes effect immediately for new transactions
# Historical transactions use rates stored on JournalEntry.exchange_rate
```

### Viewing All Exchange Rates

```python
from finance.models import Currency

for currency in Currency.objects.all():
    base_text = " (BASE)" if currency.is_base else ""
    print(f"{currency.code}: 1 {currency.code} = {currency.exchange_rate} base{base_text}")

# Output:
# QAR: 1 QAR = 1.000000 base (BASE)
# USD: 1 USD = 0.274725 base
# EUR: 1 EUR = 1.120000 base
```

---

## Migration Checklist

When switching from USD to QAR as base:

- [ ] Run: `python manage.py migrate`
- [ ] Set QAR as base currency
- [ ] Update all account currencies
- [ ] Update all product currencies  
- [ ] Update views to use new CurrencyService methods
- [ ] Test financial reports
- [ ] Verify historical transactions still valid
- [ ] Check journal entry posts work correctly
- [ ] Update frontend to display QAR by default
- [ ] Test multi-currency conversions

---

## Troubleshooting

### Issue: Reports showing wrong amounts

**Solution:** Check that:
1. Base currency is set correctly: `Currency.objects.filter(is_base=True).first()`
2. Account currencies are assigned: `Account.objects.filter(currency__isnull=True)`
3. Use `get_balance_in_currency()` or `get_balance_in_base_currency()` methods

### Issue: Old journal entries show wrong conversions

**Solution:** This is expected if you changed the base currency. The entries are correct because they store the historical rate in `JournalEntry.exchange_rate`. The entries will be re-converted to the new base currency using the rate from the transaction date.

### Issue: Product prices are doubled/halved

**Solution:** The old code was dividing when it should multiply. The new code is correct. If you have old calculations, they may need adjustment.

---

## API Examples

### REST API - Get Account in QAR

```python
# views.py
from rest_framework.response import Response
from finance.models import Account, Currency

def get_account(request, account_id):
    account = Account.objects.get(id=account_id)
    qar = Currency.objects.get(code='QAR')
    
    return Response({
        'code': account.code,
        'name': account.name,
        'balance_native': str(account.balance),
        'currency_native': account.currency.code if account.currency else 'QAR',
        'balance_qar': str(account.get_balance_in_base_currency()),
    })
```

### Template - Display Price in User's Currency

```django
<!-- prices.html -->
{% load humanize %}

Product: {{ product.name }}
<select id="currency-select" onchange="updatePrice()">
    {% for currency in currencies %}
        <option value="{{ currency.code }}" {% if currency == selected_currency %}selected{% endif %}>
            {{ currency.code }} ({{ currency.symbol }})
        </option>
    {% endfor %}
</select>

Price: <span id="price">{{ price_display }}</span>

<script>
function updatePrice() {
    const currency = document.getElementById('currency-select').value;
    fetch(`/api/products/{{ product.id }}/price/?currency=${currency}`)
        .then(r => r.json())
        .then(data => {
            document.getElementById('price').textContent = data.price_formatted;
        });
}
</script>
```

---

## Additional Resources

- Full documentation: `MULTI_CURRENCY_ARCHITECTURE.md`
- Models: `finance/models.py`
- Utilities: `core/utils.py`
- Service class: `finance/utils/currency.py`
