from django import forms
from .models import Product, Category, Supplier,ProductVariant
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
            'has_variants',
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
            'has_variants': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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
        fields = ['name', 'contact_person', 'Company_name', 'email', 'phone', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Supplier name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact person'}),
            'Company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Supplier email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Address or notes'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
ATTRIBUTE_CHOICES = [
    ("Color", "Color"),
    ("Size", "Size"),
    ("Material", "Material"),
    ("Brand", "Brand"),
    ("Custom", "Custom"),
]


class ProductVariantForm(forms.ModelForm):

    color = forms.CharField(required=False)
    size = forms.CharField(required=False)
    material = forms.CharField(required=False)
    brand = forms.CharField(required=False)
    custom = forms.CharField(required=False)

    class Meta:
        model = ProductVariant
        fields = [
            "sku",
            "additional_cost",
            "stock_quantity",
            "is_active",
        ]

    def clean(self):
        cleaned = super().clean()

        attributes = {}

        if cleaned.get("color"):
            attributes["Color"] = cleaned["color"]

        if cleaned.get("size"):
            attributes["Size"] = cleaned["size"]

        if cleaned.get("material"):
            attributes["Material"] = cleaned["material"]

        if cleaned.get("brand"):
            attributes["Brand"] = cleaned["brand"]

        if cleaned.get("custom"):
            attributes["Custom"] = cleaned["custom"]

        cleaned["attributes"] = attributes
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.attributes = self.cleaned_data["attributes"]

        if commit:
            instance.save()

        return instance


class StockAdjustmentForm(forms.Form):
    """Form for manual stock adjustments - supports both positive (add) and negative (remove) quantities"""
    ADJUSTMENT_TYPE_CHOICES = [
        ('add', 'Add Stock (Purchase/Return)'),
        ('remove', 'Remove Stock (Damage/Loss)'),
        ('purchase', 'Purchase/Restock'),
        ('return', 'Product Return'),
        ('damage', 'Damaged/Loss'),
    ]
    
    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Adjustment Type'
    )
    quantity = forms.IntegerField(
        help_text='Positive: add stock | Negative: deduct stock | Use negative values to remove items',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter quantity (+ to add, - to remove)',
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for adjustment (optional)'
        })
    )