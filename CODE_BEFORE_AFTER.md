# Code Before & After - Currency System Refactor

## 1. Account Model

### BEFORE: No Currency Tracking
```python
class Account(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), editable=False)
    # ❌ No currency field - what currency is this balance in?
    # ❌ Assumes USD everywhere
```

### AFTER: Currency-Aware
```python
class Account(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), editable=False)
    # ✓ NEW FIELD:
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True)
    # ✓ NULL = base currency, otherwise track explicit currency
    
    # ✓ NEW METHODS:
    def get_balance_in_currency(self, target_currency):
        """Convert this account's balance to a target currency."""
        from core.utils import convert_between_currencies
        # ...intelligently convertsbalance...
    
    def get_balance_in_base_currency(self):
        """Convert this account's balance to base currency."""
        base_currency = Currency.objects.filter(is_base=True).first()
        return self.get_balance_in_currency(base_currency)
```

---

## 2. Journal Entry Post Method

### BEFORE: Wrong Conversion Formula
```python
def post(self):
    """Post the journal entry to account balances."""
    if self.posted:
        raise Exception("Journal entry is already posted")
    
    self.clean()
    
    for line in self.lines.all():
        account = line.account
        
        # ❌ PROBLEM 1: Multiplies by exchange_rate
        # ❌ PROBLEM 2: Doesn't check account currency
        # ❌ PROBLEM 3: Mixes currencies without conversion
        debit_base = line.debit * self.journal.exchange_rate
        credit_base = line.credit * self.journal.exchange_rate
        
        if account.type in ['asset', 'expense']:
            account.balance += (debit_base - credit_base)  # ❌ Wrong currency!
        else:
            account.balance += (credit_base - debit_base)
        
        account.save()
    
    self.posted = True
    self.save()
```

### AFTER: Proper Multi-Currency Support
```python
def post(self):
    """Post the journal entry to account balances."""
    if self.posted:
        raise Exception("Journal entry is already posted")
    
    self.clean()
    
    for line in self.lines.all():
        account = line.account
        
        # ✓ Get account's currency (NULL = base currency)
        account_currency = account.currency or Currency.objects.filter(is_base=True).first()
        
        # ✓ Get amounts in entry's currency
        debit_amount = line.debit
        credit_amount = line.credit
        
        # ✓ Convert to account's currency if different
        if self.currency.id != account_currency.id:
            from core.utils import convert_between_currencies
            debit_amount = convert_between_currencies(
                amount=debit_amount,
                from_currency=self.currency,
                to_currency=account_currency,
                exchange_rate_snapshot=self.exchange_rate  # ✓ Use historical rate!
            )
            credit_amount = convert_between_currencies(
                amount=credit_amount,
                from_currency=self.currency,
                to_currency=account_currency,
                exchange_rate_snapshot=self.exchange_rate
            )
        
        # ✓ Apply to account in its currency
        if account.type in ['asset', 'expense']:
            account.balance += (debit_amount - credit_amount)
        else:
            account.balance += (credit_amount - debit_amount)
        
        account.save()
    
    self.posted = True
    self.save()
```

---

## 3. Journal Line Conversion Methods

### BEFORE: Simplistic Multiplication
```python
class JournalLine(models.Model):
    # ...fields...
    
    def get_debit_base(self):
        """Get debit amount converted to base currency."""
        # ❌ Simple multiplication - wrong formula
        return self.debit * self.journal.exchange_rate
    
    def get_credit_base(self):
        """Get credit amount converted to base currency."""
        # ❌ Simple multiplication - wrong formula
        return self.credit * self.journal.exchange_rate
```

### AFTER: Proper Conversion Using Utilities
```python
class JournalLine(models.Model):
    # ...fields...
    
    def get_debit_base(self):
        """Get debit amount converted to base currency.
        
        Note: This converts from the journal entry's currency to the base currency
        using the exchange rate stored on the entry (snapshot at transaction time).
        """
        from core.utils import convert_to_base_currency
        # ✓ Uses proper conversion utility
        return convert_to_base_currency(
            amount=self.debit,
            from_currency=self.journal.currency,
            exchange_rate_snapshot=self.journal.exchange_rate
        )
    
    def get_credit_base(self):
        """Get credit amount converted to base currency.
        
        Note: This converts from the journal entry's currency to the base currency
        using the exchange rate stored on the entry (snapshot at transaction time).
        """
        from core.utils import convert_to_base_currency
        # ✓ Uses proper conversion utility
        return convert_to_base_currency(
            amount=self.credit,
            from_currency=self.journal.currency,
            exchange_rate_snapshot=self.journal.exchange_rate
        )
```

---

## 4. CurrencyService

### BEFORE: Hardcoded USD Base, Inflexible
```python
from decimal import Decimal
from finance.models import Currency

class CurrencyService:
    def __init__(self, request):
        # ❌ Requires request
        self.request = request
        # ❌ Always assumes base currency exists and is unique
        self.selected_currency = self.get_selected_currency()
        self.base_currency = Currency.objects.filter(is_base=True).first()

    def get_selected_currency(self):
        # ❌ Only reads from request, no other options
        code = self.request.GET.get('currency')
        if code:
            currency = Currency.objects.filter(code=code, is_active=True).first()
            if currency:
                return currency
        return Currency.objects.filter(is_base=True).first()

    def convert(self, amount):
        # ❌ ONLY converts FROM base TO selected
        # ❌ No parameters for source/target
        if not amount:
            return Decimal('0.00')

        if not self.base_currency or self.base_currency.exchange_rate == 0:
            return amount

        # ❌ Wrong formula: dividing instead of multiplying
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
```

### AFTER: Flexible, Multi-Currency Support
```python
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
    
    # ✓ MORE FLEXIBLE INITIALIZATION
    def __init__(self, request=None, base_currency=None, selected_currency=None):
        """Initialize the currency service.
        
        Args:
            request: Optional Django request object (for getting query params)
            base_currency: Optional Currency instance to use as base. 
                          If None, uses system's configured base currency.
            selected_currency: Optional Currency instance. 
                             If None, uses base currency or request param.
        """
        self.request = request  # ✓ Request is optional now!
        self.base_currency = base_currency or get_base_currency()  # ✓ Can override
        
        if selected_currency:
            self.selected_currency = selected_currency
        elif request:
            self.selected_currency = self.get_selected_currency()
        else:
            self.selected_currency = self.base_currency

    # ... other methods ...

    # ✓ COMPLETELY NEW: Convert between ANY currencies
    def convert(self, amount, from_currency=None, to_currency=None):
        """Convert an amount between currencies.
        
        Args:
            amount (Decimal): Amount to convert
            from_currency: Source Currency instance. If None, assumes base currency.
            to_currency: Target Currency instance. If None, uses selected_currency.
        
        Returns:
            Decimal: Converted amount
        """
        if not amount:
            return Decimal('0.00')
        
        source = from_currency or self.base_currency
        target = to_currency or self.selected_currency
        
        if not source or not target:
            return Decimal(amount).quantize(Decimal('0.01'))
        
        # ✓ Uses proper conversion utility
        return convert_between_currencies(
            amount=amount,
            from_currency=source,
            to_currency=target
        )
    
    # ✓ NEW METHOD: Convert to base
    def convert_to_base(self, amount, from_currency):
        if not amount:
            return Decimal('0.00')
        if not from_currency or not self.base_currency:
            return Decimal(amount).quantize(Decimal('0.01'))
        
        return convert_to_base_currency(
            amount=amount,
            from_currency=from_currency
        )
    
    # ✓ NEW METHOD: Convert from base
    def convert_from_base(self, amount, to_currency):
        if not amount:
            return Decimal('0.00')
        if not to_currency or not self.base_currency:
            return Decimal(amount).quantize(Decimal('0.01'))
        
        return convert_from_base_currency(
            amount=amount,
            to_currency=to_currency
        )
    
    # ✓ NEW METHOD: Get exchange rate
    def get_exchange_rate(self, from_currency=None, to_currency=None):
        source = from_currency or self.base_currency
        target = to_currency or self.selected_currency
        
        if not source or not target:
            return Decimal('1.0')
        
        return get_exchange_rate_for_conversion(source, target)

    # ✓ NEW METHOD: Change base currency dynamically
    def set_base_currency(self, currency):
        """Change the base currency of the system."""
        Currency.objects.filter(is_base=True).update(is_base=False)
        currency.is_base = True
        currency.save()
        self.base_currency = currency
```

---

## 5. Product Model Conversion

### BEFORE: Wrong Formula
```python
class Product(models.Model):
    # ...fields...
    currency = models.ForeignKey('finance.Currency', ...)
    
    @property
    def discounted_price_base_currency(self):
        """Get the discounted price converted to base currency for currency conversion"""
        if not self.currency:
            return self.discounted_price
        
        # ❌ Gets base currency WRONG way
        base_currency = self.currency.__class__.objects.filter(is_base=True).first()
        if not base_currency or self.currency == base_currency:
            return self.discounted_price
        
        # ❌ DIVIDES - this is backwards!
        # If product is 100 EUR with rate 1.1, should be 110 USD
        # But this calculates: 100 / 1.1 = 90.9 (WRONG!)
        return self.discounted_price / self.currency.exchange_rate
```

### AFTER: Correct Formula with Utilities
```python
class Product(models.Model):
    # ...fields...
    currency = models.ForeignKey('finance.Currency', ...)
    
    @property
    def discounted_price_base_currency(self):
        """Get the discounted price converted to base currency.
        
        If the product's price is in a non-base currency, convert it to base currency
        using the currency's current exchange rate.
        
        Example:
            - Product price: 100 EUR
            - EUR exchange rate: 1.1 (1 EUR = 1.1 USD)  
            - Base currency: USD
            - Result: 100 * 1.1 = 110 USD  ✓
        """
        if not self.currency:
            return self.discounted_price
        
        # ✓ Uses utility functions
        from core.utils import convert_to_base_currency, get_base_currency
        
        base_currency = get_base_currency()
        if not base_currency or self.currency == base_currency:
            return self.discounted_price
        
        # ✓ Uses proper conversion with multiply
        return convert_to_base_currency(
            amount=self.discounted_price,
            from_currency=self.currency
        )
    
    # ✓ NEW METHOD: Price in any currency
    def get_price_in_currency(self, target_currency):
        """Get the discounted price converted to a specific currency."""
        from core.utils import convert_between_currencies
        
        if not self.currency or not target_currency:
            return self.discounted_price
        
        if self.currency.id == target_currency.id:
            return self.discounted_price
        
        # ✓ Can convert to ANY currency
        return convert_between_currencies(
            amount=self.discounted_price,
            from_currency=self.currency,
            to_currency=target_currency
        )
```

---

## 6. Core Utilities (NEW FILE)

### BEFORE: None
```
# No currency utilities file
# Conversions scattered throughout codebase with inconsistent logic
```

### AFTER: Comprehensive Utilities
```python
# core/utils.py - NEW FUNCTIONS

def get_base_currency():
    """Get the system's base currency."""
    from finance.models import Currency
    return Currency.objects.filter(is_base=True).first()


def convert_to_base_currency(amount, from_currency, exchange_rate_snapshot=None):
    """Convert an amount from any currency to the base currency.
    
    Formula: base_amount = amount * exchange_rate
    where exchange_rate is "1 unit of currency = X units of base"
    """
    # ✓ Centralized conversion logic
    # ✓ Supports historical rates
    # ✓ Proper formula


def convert_from_base_currency(amount, to_currency, exchange_rate_snapshot=None):
    """Convert an amount from base currency to another currency.
    
    Formula: target_amount = amount / exchange_rate
    """
    # ✓ Inverse operation
    # ✓ Centralized


def convert_between_currencies(amount, from_currency, to_currency, exchange_rate_snapshot=None):
    """Convert an amount between any two currencies.
    
    Formula: (amount * from_rate) / to_rate
    """
    # ✓ Works between ANY two currencies
    # ✓ Goes through base if needed
    # ✓ Handles special cases (same currency, etc)


def get_exchange_rate_for_conversion(from_currency, to_currency):
    """Get the exchange rate between two currencies.
    
    Returns: rate such that 1 from_currency = rate to_currency
    """
    # ✓ Can get rate between any two currencies
    # ✓ Calculates on the fly
```

---

## Usage Comparison

### Converting USD to EUR (Old vs New)

#### OLD WAY (WRONG)
```python
# ❌ Assumed base was USD
service = CurrencyService(request)
# service.base_currency was USD (hardcoded)
# service.selected_currency was whatever user chose

# ❌ Only converted FROM base
display_price = service.convert(100)  # Assumed 100 was in USD

# ❌ No way to change base currency
# ❌ If you wanted EUR base, you had to modify code
```

#### NEW WAY (CORRECT)
```python
from finance.models import Currency
from core.utils import convert_between_currencies

usd = Currency.objects.get(code='USD')
eur = Currency.objects.get(code='EUR')

# ✓ Can specify any currencies
usd_to_eur = convert_between_currencies(100, usd, eur)

# ✓ Via service too
service = CurrencyService()
usd_to_eur = service.convert(100, from_currency=usd, to_currency=eur)

# ✓ Can change base dynamically
qar = Currency.objects.get(code='QAR')
service.set_base_currency(qar)  # Now all conversions use QAR as base!
```

---

## Impact on Views

### OLD VIEW CODE (Needs Update)
```python
def product_list(request):
    service = CurrencyService(request)
    
    products = Product.objects.all()
    for product in products:
        # ❌ Assumes 100 is always in USD (base)
        product.display_price = service.convert(product.selling_price)
    
    return render(request, 'products.html', {'products': products})
```

### NEW VIEW CODE (Updated)
```python
def product_list(request):
    service = CurrencyService(request)
    
    products = Product.objects.all()
    for product in products:
        # ✓ Specifies source currency
        product.display_price = service.convert(
            product.selling_price,
            from_currency=product.currency
        )
        # ✓ Or use the convenient method:
        product.display_price = product.get_price_in_currency(
            service.selected_currency
        )
    
    return render(request, 'products.html', {'products': products})
```

---

## Migration Required

### NEW FILE: `finance/migrations/0006_account_currency.py`
```python
class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0005_journalentry_entry_type_alter_account_balance'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='currency',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='finance.currency',
            ),
        ),
    ]

# Run with: python manage.py migrate
```

---

## Conversion Formula Summary

| Operation | Formula | Example |
|-----------|---------|---------|
| Any → Base | `amount × rate` | 100 EUR × 1.1 = 110 USD |
| Base → Any | `amount ÷ rate` | 110 USD ÷ 1.1 = 100 EUR |
| Any → Any | `(amount × from_rate) ÷ to_rate` | 100 EUR → GBP = (100 × 1.1) ÷ 1.3 = 84.6 GBP |
| Base definition | `1 unit = X base units` | 1 EUR = 1.1 USD (rate = 1.1) |

---

## Key Takeaways

✅ **Centralized Conversion Logic** - All in `core/utils.py`  
✅ **Proper Formulas** - Uses multiplication/division correctly  
✅ **Historical Rates** - Stores rate on each transaction  
✅ **Flexible Base** - Can change base currency anytime  
✅ **Multi-Currency Everything** - Accounts, products, entries all support multiple currencies  
✅ **No Hardcoded USD** - Works with any base currency  
✅ **Easy to Test** - Conversion logic is testable and isolated  
