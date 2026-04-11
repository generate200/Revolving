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
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class JournalEntry(models.Model):
    """Double-entry journal entry with balanced debit/credit lines."""
    
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

            # Apply accounting rules based on account type using base currency amounts
            debit_base = line.get_debit_base()
            credit_base = line.get_credit_base()
            
            if account.type in ['asset', 'expense']:
                account.balance += (debit_base - credit_base)
            else:
                account.balance += (credit_base - debit_base)

            account.save()

        self.posted = True
        self.save()

    def reverse(self):
        """Create a reversal entry with debits and credits flipped."""
        if not self.posted:
            raise Exception("Only posted entries can be reversed")

        reversal = JournalEntry.objects.create(
            date=timezone.now().date(),
            description=f"Reversal of JE {self.id}",
            memo=f"Reversal of: {self.description}",
            currency=self.currency,
            exchange_rate=self.exchange_rate
        )

        for line in self.lines.all():
            JournalLine.objects.create(
                journal=reversal,
                account=line.account,
                debit=line.credit,
                credit=line.debit,
                comment="Reversal entry"
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

    def __str__(self):
        currency_symbol = self.journal.currency.symbol if hasattr(self, 'journal') and self.journal else '$'
        return f"{self.account.name} | Dr:{currency_symbol}{self.debit} Cr:{currency_symbol}{self.credit}"

    def get_debit_base(self):
        """Get debit amount converted to base currency."""
        return self.debit * self.journal.exchange_rate

    def get_credit_base(self):
        """Get credit amount converted to base currency."""
        return self.credit * self.journal.exchange_rate

    def clean(self):
        """Validate that only one of debit or credit is set."""
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("A line cannot have both debit and credit amounts")
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("A line must have either a debit or credit amount")
        if self.debit < 0 or self.credit < 0:
            raise ValidationError("Amounts must be positive")
    
    
