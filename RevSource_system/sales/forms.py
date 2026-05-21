from django import forms
from django.forms import formset_factory, modelformset_factory
from .models import SalesInvoice, SalesLine, Payment
from products.models import Product


class SalesLineForm(forms.ModelForm):
    """Form for individual line items in an invoice - validates available inventory"""
    class Meta:
        model = SalesLine
        fields = ['product', 'variant', 'quantity', 'unit_price', 'discount', 'tax']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'variant': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1',
                'min': '0.01'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'discount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'tax': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
        }
    
    def clean(self):
        """Validate that requested quantity doesn't exceed available stock"""
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if product and quantity:
            available = product.available_stock
            if quantity > available:
                raise forms.ValidationError(
                    f'Insufficient inventory for {product.name}. '
                    f'Available: {available}, Requested: {quantity}'
                )
        
        return cleaned_data


SalesLineFormSet = modelformset_factory(
    SalesLine,
    form=SalesLineForm,
    extra=1,
    can_delete=True
)


class SalesInvoiceForm(forms.ModelForm):
    """Form for creating/editing invoices"""
    class Meta:
        model = SalesInvoice
        fields = ['customer', 'currency', 'discount_total']
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-control',
                'id': 'customer-select'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-control',
                'id': 'currency-select'
            }),
            'discount_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'id': 'discount-total'
            }),
        }


class PaymentForm(forms.ModelForm):
    """Form for recording payments"""
    class Meta:
        model = Payment
        fields = ['method', 'amount', 'reference']
        widgets = {
            'method': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01'
            }),
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: Card ID, Check number, etc'
            }),
        }


class QuickProductSearchForm(forms.Form):
    """Form for quick product search in POS"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'product-search',
            'placeholder': 'Search by name, SKU, or barcode...',
            'autocomplete': 'off'
        })
    )
