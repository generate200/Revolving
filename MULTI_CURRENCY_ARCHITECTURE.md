# Multi-Currency Architecture - Complete Guide

## Overview
This document explains the refactored multi-currency system that now supports flexible base currency configuration and proper currency conversions across all entities (accounts, products, journal entries).

## Key Changes

### 1. **Account Currency Tracking** 
Account balances now explicitly track their currency. Previously, all accounts implicitly assumed USD as base.

**Before:**
```python
class Account(models.Model):
    balance = Decimal('100.00')  # Was this USD? EUR? Unknown!
```

**After:**
```python
class Account(models.Model):
    balance = Decimal('100.00')  # In account.currency (or base if NULL)
    currency = ForeignKey(Currency, null=True)  # Track the currency explicitly
```

**Migration:** Applied in `0006_account_currency.py`

---

### 2. **Currency Conversion Formulas**

The system now uses proper exchange rate math. All exchange rates are stored as:
```
1 unit of Currency = X units of Base Currency
```

#### Converting To Base Currency
```
base_amount = amount × currency.exchange_rate
```
**Example:** 100 EUR with rate 1.1 → 100 × 1.1 = 110 USD

#### Converting From Base Currency  
```
target_amount = amount ÷ currency.exchange_rate
```
**Example:** 110 USD → 110 ÷ 1.1 = 100 EUR

#### Converting Between Any Two Currencies
```
target_amount = (amount × source_rate) ÷ target_rate
```

---

## Core Utilities (`core/utils.py`)

### `get_base_currency()`
Returns the system's base currency.
```python
base = get_base_currency()  # Returns Currency with is_base=True
```

### `convert_to_base_currency(amount, from_currency, exchange_rate_snapshot=None)`
Converts any currency amount to base currency.

**Parameters:**
- `amount` (Decimal) - Amount to convert
- `from_currency` (Currency) - Source currency
- `exchange_rate_snapshot` (Decimal, optional) - Use historical rate (for past transactions)

**Example:**
```python
from core.utils import convert_to_base_currency

# Current rate
usd_amount = convert_to_base_currency(100, eur_currency)  # 110 USD

# Historical rate (for journal entries posted on specific dates)
usd_amount = convert_to_base_currency(100, eur_currency, exchange_rate_snapshot=Decimal('1.15'))  # 115 USD
```

### `convert_from_base_currency(amount, to_currency, exchange_rate_snapshot=None)`
Converts from base currency to target currency.

**Example:**
```python
eur_amount = convert_from_base_currency(110, eur_currency)  # 100 EUR
```

### `convert_between_currencies(amount, from_currency, to_currency, exchange_rate_snapshot=None)`
Converts between any two currencies.

**Example:**
```python
# Convert 100 EUR to GBP
gbp_amount = convert_between_currencies(100, eur_currency, gbp_currency)
```

### `get_exchange_rate_for_conversion(from_currency, to_currency)`
Gets the exchange rate between two currencies.

**Example:**
```python
rate = get_exchange_rate_for_conversion(eur_currency, usd_currency)
# Returns: 1.1 (meaning 1 EUR = 1.1 USD)
```

---

## CurrencyService (`finance/utils/currency.py`)

### Initialization
**Old way (single base currency):**
```python
service = CurrencyService(request)  # Assumed USD as base
```

**New way (flexible base currency):**
```python
# Use system base currency
service = CurrencyService(request)

# Use specific base currency
qar_as_base = Currency.objects.get(code='QAR')
service = CurrencyService(request, base_currency=qar_as_base)

# Without request object
service = CurrencyService(base_currency=qar_as_base)
```

### Methods

#### `convert(amount, from_currency=None, to_currency=None)`
Converts between currencies. If `from_currency` is None, assumes base currency.

**Old way:**
```python
# Only converted FROM base TO selected currency
usd_price = 100
display_price = service.convert(usd_price)  # In selected currency
```

**New way:**
```python
# Can convert from any currency to any currency
usd_price = 100
eur_price = service.convert(100, from_currency=usd_ccy, to_currency=eur_ccy)

# Special case: shorthand for converting to selected currency
display_price = service.convert(100, from_currency=usd_ccy)  # Uses selected_currency as target
```

#### `convert_to_base(amount, from_currency)`
Converts amount to base currency.

```python
usd_amount = service.convert_to_base(100, eur_currency)
```

#### `convert_from_base(amount, to_currency)`
Converts from base to target currency.

```python
eur_amount = service.convert_from_base(110, eur_currency)
```

#### `get_exchange_rate(from_currency=None, to_currency=None)`
Gets exchange rate between two currencies.

```python
rate = service.get_exchange_rate(eur_currency, usd_currency)  # 1.1
rate = service.get_exchange_rate()  # Between base and selected
```

#### `set_base_currency(currency)`
⚠️ **IMPORTANT:** Change the system's base currency.

```python
qar = Currency.objects.get(code='QAR')
service.set_base_currency(qar)  # Now QAR is base

# All conversions now use QAR as base
```

---

## Model Changes

### Account Model
**New fields:**
- `currency` - ForeignKey to Currency (NULL = base currency)

**New methods:**
```python
account = Account.objects.get(code='1000')

# Get balance in specific currency
balance_eur = account.get_balance_in_currency(eur_currency)

# Get balance in base currency
balance_base = account.get_balance_in_base_currency()
```

### JournalEntry & JournalLine
These now properly handle multi-currency posting:

**Before:** 
- Only converted to base using current rates ❌
- Didn't track what currency each account was in ❌

**After:**
- Uses historical exchange rates from transaction date ✓
- Converts to each account's currency ✓
- Supports changing base currency without breaking history ✓

**Example - Posting a journal entry in EUR:**
```python
# Create entry in EUR with rate 1.1 (captured on transaction date)
entry = JournalEntry.objects.create(
    date=date.today(),
    currency=eur_currency,
    exchange_rate=Decimal('1.1')  # Rate on transaction date
)

# Add lines
entry.add_line(account_usd, debit=110)  # Debit USD account
entry.add_line(account_eur, credit=100)  # Credit EUR account

# Post - automatically converts to each account's currency
entry.post()
```

### Product Model
**New method:**
```python
product = Product.objects.get(sku='PROD001')

# Get price in specific currency
price_eur = product.get_price_in_currency(eur_currency)
```

**Fixed property:**
```python
# Was dividing (WRONG), now multiplies (CORRECT)
base_price = product.discounted_price_base_currency  # Uses proper conversion
```

---

## Migration Guide

### If Changing Base Currency (e.g., USD → QAR)

#### Step 1: Set QAR as Base Currency
```python
from finance.models import Currency
from finance.utils.currency import CurrencyService

qar = Currency.objects.get(code='QAR')
service = CurrencyService()
service.set_base_currency(qar)
```

#### Step 2: Update Account Currencies (Optional)
If you want accounts to track their currency explicitly:

```python
from finance.models import Account, Currency

usd = Currency.objects.get(code='USD')
eur = Currency.objects.get(code='EUR')

# Mark which accounts are in which currency
for account in Account.objects.all():
    if account.code.startswith('1'):  # Example: Asset accounts in USD
        account.currency = usd
    elif account.code.startswith('4'):  # Revenue accounts in EUR
        account.currency = eur
    account.save()
```

#### Step 3: Run Migration
```bash
python manage.py migrate finance 0006_account_currency
```

#### Step 4: Verify Reports
Check that financial reports now show correct conversions with QAR as base.

---

## Usage Examples

### Example 1: Multi-Currency Sales
```python
from finance.models import JournalEntry, Account, Currency
from decimal import Decimal

# Set up currencies
usd = Currency.objects.get(code='USD')
eur = Currency.objects.get(code='EUR')
eur.exchange_rate = Decimal('1.10')  # 1 EUR = 1.10 USD
eur.save()

# Create accounts in different currencies
cash_usd = Account.objects.create(code='1010', name='Cash USD', type='asset', currency=usd)
cash_eur = Account.objects.create(code='1020', name='Cash EUR', type='asset', currency=eur)
revenue = Account.objects.create(code='4000', name='Revenue', type='revenue')

# Post a sale in EUR for 100 EUR
entry = JournalEntry.objects.create(
    date=datetime.date.today(),
    currency=eur,
    exchange_rate=Decimal('1.10'),
    description='Sale in EUR'
)
entry.add_line(cash_eur, credit=100)  # Receive 100 EUR
entry.add_line(revenue, debit=100)    # Revenue 100 EUR

entry.post()

# Results:
# cash_eur.balance = 100 EUR (stored in EUR)
# revenue.balance = 110 USD (base currency amount, if revenue is in USD)
```

### Example 2: Querying Accounts in Different Currencies
```python
from core.utils import convert_between_currencies

# Get total assets in EUR
assets = Account.objects.filter(type='asset')
total_eur = Decimal('0')

for asset in assets:
    balance_eur = asset.get_balance_in_currency(eur)
    total_eur += balance_eur

print(f"Total assets in EUR: {total_eur}")
```

### Example 3: Product Pricing
```python
# Product in EUR
product = Product.objects.create(
    name='Widget',
    selling_price=Decimal('100'),
    currency=eur
)

# Display in different currencies
price_usd = product.get_price_in_currency(usd)  # Will be ~110
price_qar = product.get_price_in_currency(qar)
```

---

## Common Pitfalls & Solutions

### ❌ WRONG: Assuming all amounts are in USD
```python
def old_get_balance(account):
    return account.balance  # Could be in any currency!
```

### ✓ RIGHT: Track and convert currencies
```python
def get_balance_in_usd(account):
    return account.get_balance_in_currency(usd_currency)
```

---

### ❌ WRONG: Using current exchange rates for historical transactions
```python
def post_old_entry(entry):
    # Uses TODAY's EUR rate, but entry is from 2020!
    for line in entry.lines.all():
        line.balance = line.amount * Currency.objects.get(code='EUR').exchange_rate
```

### ✓ RIGHT: Use historical rates from transaction
```python
def post_new_entry(entry):
    # Uses exchange_rate stored on entry from transaction date
    for line in entry.lines.all():
        base_amount = line.amount * entry.exchange_rate  # Correct!
```

---

## Configuration

### System Base Currency
Currently set via admin or manually:
```python
# In Django admin:
# 1. Go to Finance > Currencies
# 2. Check "Is Base" for QAR (only one can be base)

# Or programmatically:
from finance.utils.currency import CurrencyService
qar = Currency.objects.get(code='QAR')
CurrencyService().set_base_currency(qar)
```

### Adding New Currencies
```python
from finance.models import Currency
from decimal import Decimal

Currency.objects.create(
    code='AED',
    name='United Arab Emirates Dirham',
    symbol='د.إ',
    exchange_rate=Decimal('3.6725'),  # 1 AED = 3.6725 base currency
    is_active=True
)
```

---

## Benefits of New Architecture

✅ **Flexible Base Currency** - Change from USD to QAR without code changes  
✅ **Historical Accuracy** - Past transactions use rates from their date  
✅ **Multi-Currency Accounts** - Each account explicitly tracks its currency  
✅ **Proper Math** - Correct conversion formulas for all scenarios  
✅ **Product Pricing** - Products can be priced in any currency  
✅ **Full Auditability** - All conversion rates are recorded  
✅ **Easy to Test** - Conversion logic is centralized and testable  

---

## Testing

```python
from decimal import Decimal
from core.utils import convert_between_currencies, get_base_currency

# Test basic conversion
eur = Currency.objects.get(code='EUR')
usd = Currency.objects.get(code='USD')

amount_eur = Decimal('100')
amount_usd = convert_between_currencies(amount_eur, eur, usd)
print(f"100 EUR = {amount_usd} USD")  # Should be 110

# Test reverse
amount_eur_2 = convert_between_currencies(amount_usd, usd, eur)
print(f"{amount_usd} USD = {amount_eur_2} EUR")  # Should be ~100
```

---

## Next Steps

1. ✅ Run migration: `python manage.py migrate`
2. ✅ Set base currency to QAR (if desired)
3. ✅ Update account currencies (assign to USD/EUR/QAR)
4. ✅ Update existing views to use new CurrencyService methods
5. ✅ Test all financial reports with new conversions
6. ✅ Verify historical journal entries still post correctly
