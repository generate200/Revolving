from django.db import models
from django.db.models import F
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DeleteView, TemplateView
from .models import Product, Category, Supplier
from .forms import ProductForm, CategoryForm, SupplierForm
from finance.models import Currency
from finance.utils.currency import CurrencyService


class IndexView(TemplateView):
    template_name = 'products/index.html'


class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 25

    def get_currency_service(self):
        if not hasattr(self, '_currency_service'):
            self._currency_service = CurrencyService(self.request)
        return self._currency_service

    def get_queryset(self):
        queryset = Product.objects.select_related('category', 'currency').order_by('name')
        currency_service = self.get_currency_service()

        for product in queryset:
            product.converted_price = currency_service.convert(
                product.discounted_price_base_currency
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        currency_service = self.get_currency_service()

        queryset = self.object_list  # ✅ use already-evaluated queryset

        context['total_products'] = queryset.count()
        context['low_stock_count'] = queryset.filter(
            stock_quantity__lte=F('reorder_point')
        ).count()

        currencies = Currency.objects.filter(is_active=True)
        base_currency = currencies.filter(is_base=True).first()
        selected_currency = self.request.GET.get('currency')

        if selected_currency:
            selected_obj = currencies.filter(code=selected_currency).first()
        else:
            selected_obj = base_currency

        context['currency_symbol']=selected_obj.symbol if selected_obj else '$'
        context['currencies'] = currencies

        context['currency_data'] = {
            "baseCurrency": base_currency.code if base_currency else "USD",
            "currencies": {
                c.code: {
                    "symbol": c.symbol,
                    "exchange_rate": float(c.exchange_rate)
                }
                for c in currencies
            }
        }

        return context


class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('products:list')


class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'products/product_confirm_delete.html'
    success_url = reverse_lazy('products:list')

class create_categoryView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'products/category_form.html'
    success_url = reverse_lazy('products:category-list')

class ProductcategoryListView(ListView):
    model = Category
    template_name = 'products/product_category_list.html'
    context_object_name = 'categories'
    paginate_by = 25

    def get_queryset(self):
        return Category.objects.annotate(product_count=models.Count('product')).order_by('name')

class create_supplierView(CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'products/supplier_form.html'
    success_url = reverse_lazy('products:supplier-list')


class ProductSupplierListView(ListView):
    model = Supplier
    template_name = 'products/product_supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 25

    def get_queryset(self):
        return Supplier.objects.annotate(product_count=models.Count('product')).order_by('name')

class category_deleteview(DeleteView):
    model = Category
    template_name = 'products/category_confirm_delete.html'
    success_url = reverse_lazy('products:category-list')

class supplier_deleteview(DeleteView):
    model = Supplier
    template_name = 'products/supplier_confirm_delete.html'
    success_url = reverse_lazy('products:supplier-list') 