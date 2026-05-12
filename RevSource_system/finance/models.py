from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Currency(models.Model):
    """Currency definitions for multi-currency support."""
    
    code = models.CharField(max_length=3, unique=True, help_text="ISO currency code (e.g., USD, EUR, QAR)")
    name = models.CharField(max_length=100, help_text="Currency name (e.g., US Dollar, Euro, Qatari Riyal)")
    symbol = models.CharField(max_length=10, help_text="Currency symbol (e.g., $, €, ر.ق)")
    decimal_places = models.PositiveIntegerField(default=2, help_text="Number of decimal places")
    is_active = models.BooleanField(default=True)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal('1.000000'), 
                                       help_text="Exchange rate to base currency (1.0 = base currency)")
    is_base = models.BooleanField(default=False, help_text="Is this the base currency for the system?")
    
    class Meta:
        verbose_name_plural = "currencies"
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        # Ensure only one base currency
        if self.is_base:
            Currency.objects.filter(is_base=True).exclude(pk=self.pk).update(is_base=False)
        super().save(*args, **kwargs)


class Account(models.Model):
    """Chart of Accounts for double-entry bookkeeping."""
    
    ACCOUNT_TYPES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]
    
    code = models.CharField(max_length=20, unique=True, help_text="Account code (e.g., E1000, L2000,X003)")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    description = models.TextField(blank=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'), editable=False,
                                 help_text="Balance in the account's currency")
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True,
                                help_text="Currency in which this account's balance is stored. NULL means base currency.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['code']
        indexes = [
            models.Index(fields=['type', 'is_active'], name='account_type_active_idx'),
            models.Index(fields=['is_active', 'code'], name='account_active_code_idx'),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def get_balance_in_currency(self, target_currency):
        """Convert this account's balance to a target currency.
        
        Args:
            target_currency: Currency instance to convert to
            
        Returns:
            Balance converted to target currency
        """
        from core.utils import convert_between_currencies
        
        account_currency = self.currency or Currency.objects.filter(is_base=True).first()
        if not account_currency or not target_currency:
            return self.balance
        
        if account_currency.id == target_currency.id:
            return self.balance
        
        return convert_between_currencies(
            amount=self.balance,
            from_currency=account_currency,
            to_currency=target_currency
        )
    
    def get_balance_in_base_currency(self):
        """Convert this account's balance to base currency."""
        base_currency = Currency.objects.filter(is_base=True).first()
        if not base_currency:
            return self.balance
        
        return self.get_balance_in_currency(base_currency)


class JournalEntry(models.Model):
    """Double-entry journal entry with balanced debit/credit lines."""
    ENTRY_TYPES = [
        ('normal','Normal'),
        ('opening','OpeningBalance'),
        ('reversal','Reversal'),
        ]
    entry_type=models.CharField(max_length=20,choices=ENTRY_TYPES,default='normal')
    date = models.DateField()
    description = models.TextField()
    memo = models.CharField(max_length=255, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default=1, 
                                help_text="Currency for this journal entry")
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6, default=Decimal('1.000000'),
                                       help_text="Exchange rate used for this entry")
    posted = models.BooleanField(default=False, help_text="Prevents double posting and modification")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['date'], name='journalentry_date_idx'),
            models.Index(fields=['created_by'], name='journalentry_created_by_idx'),
            models.Index(fields=['posted'], name='journalentry_posted_idx'),
        ]

    def __str__(self):
        return f"JE {self.id} - {self.date} ({self.currency.code})"

    def is_balanced(self):
        """Check if total debits equal total credits."""
        total_debit = self.lines.aggregate(models.Sum('debit'))['debit__sum'] or Decimal('0.00')
        total_credit = self.lines.aggregate(models.Sum('credit'))['credit__sum'] or Decimal('0.00')
        return total_debit == total_credit

    def get_total_debit(self):
        return self.lines.aggregate(models.Sum('debit'))['debit__sum'] or Decimal('0.00')

    def get_total_credit(self):
        return self.lines.aggregate(models.Sum('credit'))['credit__sum'] or Decimal('0.00')

    def clean(self):
        """Validate journal entry. Note: Some validations require the instance to be saved first."""
        # Basic validations that don't require related objects
        pass

    def post(self):
        """Post the journal entry to account balances. This is irreversible."""
        if self.posted:
            raise Exception("Journal entry is already posted")

        self.clean()

        for line in self.lines.all():
            account = line.account
            
            # Determine the account's currency (defaults to base currency)
            account_currency = account.currency or Currency.objects.filter(is_base=True).first()
            
            # Get the debit/credit amounts in the journal entry's currency
            debit_amount = line.debit
            credit_amount = line.credit
            
            # Convert to account's currency if different from journal entry currency
            if self.currency.id != account_currency.id:
                from core.utils import convert_between_currencies
                debit_amount = convert_between_currencies(
                    amount=debit_amount,
                    from_currency=self.currency,
                    to_currency=account_currency,
                    exchange_rate_snapshot=self.exchange_rate  # Use the rate from the entry date
                )
                credit_amount = convert_between_currencies(
                    amount=credit_amount,
                    from_currency=self.currency,
                    to_currency=account_currency,
                    exchange_rate_snapshot=self.exchange_rate
                )

            # Apply accounting rules based on account type
            if account.type in ['asset', 'expense']:
                account.balance += (debit_amount - credit_amount)
            else:
                account.balance += (credit_amount - debit_amount)

            account.save()

        self.posted = True
        self.save()

    def reverse(self):
        """Create a reversal entry with debits and credits flipped."""
        if not self.posted:
            raise Exception("Only posted entries can be reversed")
        if self.entry_type == 'opening':
            raise Exception("Opening balance entries cannot be reversed")
        
        reversal = JournalEntry.objects.create(
            date=timezone.now().date(),
            description=f"Reversal of JE {self.id}",
            memo=f"Reversal of: {self.description}",
            currency=self.currency,
            exchange_rate=self.exchange_rate,
            entry_type='reversal'
        )

        for line in self.lines.all():
            JournalLine.objects.create(
                journal=reversal,
                account=line.account,
                debit=line.credit,
                credit=line.debit,
                comment=f"Reversal of line {line.id} from JE {self.id}"
            )

        reversal.post()
        return reversal

    def add_line(self, account, debit=Decimal('0.00'), credit=Decimal('0.00'), comment=None):
        """Convenience method to add a debit or credit line."""
        if debit < 0 or credit < 0:
            raise ValueError("Debit and credit amounts must be non-negative")
        if debit > 0 and credit > 0:
            raise ValueError("A line cannot have both debit and credit")
        
        return JournalLine.objects.create(
            journal=self,
            account=account,
            debit=debit,
            credit=credit,
            comment=comment
        )


class JournalLine(models.Model):
    """Individual debit or credit line in a journal entry."""
    
    journal = models.ForeignKey(JournalEntry, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    comment = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['account'], name='journalline_account_idx'),
        ]

    def __str__(self):
        currency_symbol = self.journal.currency.symbol if hasattr(self, 'journal') and self.journal else '$'
        return f"{self.account.name} | Dr:{currency_symbol}{self.debit} Cr:{currency_symbol}{self.credit}"

    def get_debit_base(self):
        """Get debit amount converted to base currency.
        
        Note: This converts from the journal entry's currency to the base currency
        using the exchange rate stored on the entry (snapshot at transaction time).
        """
        from core.utils import convert_to_base_currency
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
        return convert_to_base_currency(
            amount=self.credit,
            from_currency=self.journal.currency,
            exchange_rate_snapshot=self.journal.exchange_rate
        )

    def clean(self):
        """Validate that only one of debit or credit is set."""
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("A line cannot have both debit and credit amounts")
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("A line must have either a debit or credit amount")
        if self.debit < 0 or self.credit < 0:
            raise ValidationError("Amounts must be positive")
    
    
