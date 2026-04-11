from django import forms
from .models import Product, Category, Supplier
from finance.models import Currency


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name',
            'sku',
            'barcode',
            'category',
            'supplier',
            'currency',
            'cost_price',
            'selling_price',
            'discount_percentage',
            'stock_quantity',
            'reorder_point',
            'unit',
            'weight',
            'dimensions',
            'description',
            'image',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique SKU'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional barcode'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'reorder_point': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dimensions': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10x20x30 cm'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Product description and notes'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_discount_percentage(self):
        discount = self.cleaned_data.get('discount_percentage')
        if discount is None:
            return 0
        return discount

    def clean(self):
        cleaned_data = super().clean()
        cost_price = cleaned_data.get('cost_price')
        selling_price = cleaned_data.get('selling_price')
        if cost_price is not None and selling_price is not None and selling_price < cost_price:
            self.add_error('selling_price', 'Selling price should typically be higher than cost price.')
        return cleaned_data


class CategoryForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        queryset=Category.objects.order_by('name'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='No parent category'
    )

    class Meta:
        model = Category
        fields = ['name', 'description', 'parent', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Optional description'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Supplier name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact person'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Supplier email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address or notes'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
