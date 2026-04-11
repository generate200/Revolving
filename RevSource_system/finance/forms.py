from django import forms
from django.forms import inlineformset_factory
from decimal import Decimal
from django.core.exceptions import ValidationError
from .models import JournalEntry, JournalLine, Account, Currency


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['date', 'description', 'memo', 'currency', 'exchange_rate']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the transaction'
            }),
            'memo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Short reference code (optional)'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_currency'
            }),
            'exchange_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': '1.000000',
                'id': 'id_exchange_rate'
            }),
        }


class JournalLineForm(forms.ModelForm):
    order = forms.IntegerField(required=False, widget=forms.HiddenInput())
    
    class Meta:
        model = JournalLine
        fields = ['account', 'debit', 'credit', 'comment']
        widgets = {
            'account': forms.Select(attrs={
                'class': 'form-select account-select',
                'placeholder': 'Choose account...'
            }),
            'debit': forms.NumberInput(attrs={
                'class': 'form-control amount-input debit-input',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'credit': forms.NumberInput(attrs={
                'class': 'form-control amount-input credit-input',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'comment': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Line comment'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        debit = cleaned_data.get('debit')
        credit = cleaned_data.get('credit')
        account = cleaned_data.get('account')

        # Convert None to Decimal('0.00')
        debit = debit if debit is not None else Decimal('0.00')
        credit = credit if credit is not None else Decimal('0.00')

        # If this is an empty form (no account, no amounts), don't validate
        if not account and debit == Decimal('0.00') and credit == Decimal('0.00'):
            return cleaned_data

        # For non-empty forms, require account
        if not account:
            raise forms.ValidationError("Account is required")

        if debit > 0 and credit > 0:
            raise forms.ValidationError("A line cannot have both debit and credit amounts")
        
        if debit == 0 and credit == 0:
            raise forms.ValidationError("A line must have either a debit or credit amount")

        return cleaned_data


JournalLineFormSet = inlineformset_factory(
    JournalEntry, 
    JournalLine,
    form=JournalLineForm,
    extra=3,
    can_delete=True,
    min_num=2,  # Require at least 2 lines
    validate_min=True
)


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'type', 'description', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'A01000',
                'maxlength': '20'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account name'
            }),
            'type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Account description'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean(self):
        """Validate account code and name uniqueness."""
        cleaned_data = super().clean()
        code = cleaned_data.get('code')
        name = cleaned_data.get('name')

        # Check for duplicate account code
        if code:
            code = code.strip().upper()
            cleaned_data['code'] = code
            
            existing_code = Account.objects.filter(code__iexact=code).first()
            if existing_code:
                raise ValidationError(
                    f"Account code '{code}' already exists. "
                    f"Account: {existing_code.name} ({existing_code.get_type_display()}). "
                    f"Use a different code or edit the existing account."
                )

        # Check for similar account names (case-insensitive)
        if name:
            name = name.strip()
            cleaned_data['name'] = name
            
            existing_name = Account.objects.filter(name__iexact=name).first()
            if existing_name:
                raise ValidationError(
                    f"Account name '{name}' already exists ({existing_name.code}). "
                    f"Choose a different name."
                )

        return cleaned_data

    def clean_code(self):
        """Clean and validate account code format."""
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip().upper()
            if not code:
                raise ValidationError("Account code cannot be empty")
            if len(code) < 2:
                raise ValidationError("Account code must be at least 2 characters")
        return code

    def clean_name(self):
        """Clean account name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if not name:
                raise ValidationError("Account name cannot be empty")
        return name


class CurrencyForm(forms.ModelForm):
    class Meta:
        model = Currency
        fields = ['code', 'name', 'symbol', 'decimal_places', 'exchange_rate', 'is_base', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'USD',
                'maxlength': '3'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'US Dollar'
            }),
            'symbol': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '$'
            }),
            'decimal_places': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '6'
            }),
            'exchange_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'placeholder': '1.000000'
            }),
            'is_base': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def clean_code(self):
        """Validate currency code format."""
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip().upper()
            if len(code) != 3:
                raise ValidationError("Currency code must be exactly 3 characters")
            if not code.isalpha():
                raise ValidationError("Currency code must contain only letters")
        return code

    def clean(self):
        cleaned_data = super().clean()
        is_base = cleaned_data.get('is_base')
        exchange_rate = cleaned_data.get('exchange_rate')

        # Base currency should have exchange rate of 1.0
        if is_base and exchange_rate and exchange_rate != Decimal('1.000000'):
            raise ValidationError("Base currency must have exchange rate of 1.000000")

        return cleaned_data

