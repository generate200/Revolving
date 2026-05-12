from django.db import models
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.decorators import method_decorator
from .models import Product, Category, Supplier, ProductVariant
from .forms import ProductForm, CategoryForm, SupplierForm, ProductVariantForm, StockAdjustmentForm
from finance.models import Currency
from finance.utils.currency import CurrencyService
from sales.models import StockMovement
from core.exporters import DataExporter


class IndexView(TemplateView):
    template_name = 'products/index.html'


@method_decorator(login_required, name='dispatch')
class InventoryView(TemplateView):
    template_name = 'products/inventory.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = Product.objects.select_related('category', 'supplier').order_by('name')
        stock_movements = StockMovement.objects.select_related('product').order_by('-created_at')[:25]

        low_stock_products = [
            p for p in products
            if p.available_stock <= p.reorder_point
        ]

        total_inventory_value = sum(
            (p.cost_price or 0) * p.available_stock
            for p in products
        )
        available_stock = sum(p.available_stock for p in products)
        out_of_stock_count = sum(1 for p in products if p.available_stock == 0)
        damaged_stock = StockMovement.objects.filter(
            movement_type='adjustment',
            reference__icontains='damage'
        ).aggregate(models.Sum('quantity'))['quantity__sum'] or 0

        # Fast moving products by movement quantity
        fast_moving_qs = StockMovement.objects.values(
            'product__name', 'product__sku'
        ).annotate(total_quantity=models.Sum('quantity')).order_by('-total_quantity')[:3]
        fast_moving_products = [
            {
                'label': f"{item['product__name']} ({item['product__sku']})",
                'quantity': item['total_quantity'] or 0,
            }
            for item in fast_moving_qs
        ]

        # Dead stock: products with no movement or no recent movement
        recent_cutoff = timezone.now() - timezone.timedelta(days=90)
        active_product_ids = set(StockMovement.objects.filter(
            created_at__gte=recent_cutoff
        ).values_list('product_id', flat=True).distinct())

        dead_stock_products = [
            p for p in products
            if p.id not in active_product_ids and p.available_stock > 0
        ][:3]
        dead_stock_count = len(dead_stock_products)

        # Stock aging: products with older movement history
        aging_cutoff = timezone.now() - timezone.timedelta(days=90)
        aging_products_qs = [
            p for p in products
            if p.stock_movements.exists() and p.stock_movements.latest('created_at').created_at < aging_cutoff
        ]
        stock_aging_count = len(aging_products_qs)
        stock_aging_products = aging_products_qs[:3]

        movement_summary_qs = StockMovement.objects.values('movement_type').annotate(
            total_quantity=models.Sum('quantity')
        ).order_by('-total_quantity')

        movement_type_labels = dict(StockMovement.MOVEMENT_TYPES)
        movement_summary = []
        max_movement_qty = max((item['total_quantity'] or 0) for item in movement_summary_qs) if movement_summary_qs else 0
        for item in movement_summary_qs:
            qty = item['total_quantity'] or 0
            percent = int((qty / max_movement_qty) * 100) if max_movement_qty > 0 else 0
            movement_summary.append({
                'type': item['movement_type'],
                'label': movement_type_labels.get(item['movement_type'], item['movement_type'].title()),
                'total_quantity': qty,
                'percent': percent,
            })

        top_moving_products_qs = StockMovement.objects.values(
            'product__name', 'product__sku'
        ).annotate(total_quantity=models.Sum('quantity')).order_by('-total_quantity')[:6]
        max_top_qty = max((item['total_quantity'] or 0) for item in top_moving_products_qs) if top_moving_products_qs else 0
        top_moving_products = []
        for item in top_moving_products_qs:
            qty = item['total_quantity'] or 0
            percent = int((qty / max_top_qty) * 100) if max_top_qty > 0 else 0
            top_moving_products.append({
                'label': f"{item['product__name']} ({item['product__sku']})",
                'total_quantity': qty,
                'percent': percent,
            })

        base_currency = Currency.objects.filter(is_base=True).first()
        context.update({
            'products': products,
            'stock_movements': stock_movements,
            'low_stock_products': low_stock_products,
            'total_inventory_value': total_inventory_value,
            'available_stock': available_stock,
            'low_stock_count': len(low_stock_products),
            'out_of_stock_count': out_of_stock_count,
            'damaged_stock_quantity': damaged_stock,
            'pending_transfers': 0,
            'movement_summary': movement_summary,
            'top_moving_products': top_moving_products,
            'fast_moving_products': fast_moving_products,
            'dead_stock_count': dead_stock_count,
            'dead_stock_products': dead_stock_products,
            'stock_aging_count': stock_aging_count,
            'stock_aging_products': stock_aging_products,
            'currency_symbol': base_currency.symbol if base_currency else '$',
            'base_currency_code': base_currency.code if base_currency else 'USD',
        })
        return context


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
            # Convert product price from its currency to selected currency
            product.converted_price = currency_service.convert(
                product.discounted_price,
                from_currency=product.currency,
                to_currency=currency_service.selected_currency
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
    
        currency_code = self.request.GET.get('currency')
        if currency_code:
            self.request.session['currency'] = currency_code
        currency_code = self.request.session.get('currency', 'USD')
        selected_obj = currencies.filter(code=currency_code).first()
        if not selected_obj:
            selected_obj = base_currency

        context['currency_symbol']=selected_obj.symbol if selected_obj else '$'
        context['currencies'] = currencies
        context['selected_currency'] = selected_obj

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
class ProductDetailView(TemplateView):
    template_name = 'products/product_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        product = get_object_or_404(
            Product.objects.select_related(
                'category',
                'supplier',
                'currency'
            ).prefetch_related('variants'),
            pk=self.kwargs['pk']
        )

        context["product"] = product

        currency_service = CurrencyService(self.request)
        context["converted_price"] = currency_service.convert(
            product.discounted_price,
            from_currency=product.currency,
            to_currency=currency_service.selected_currency
        )

        return context
class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('products:list')

    def form_invalid(self, form):
        print(form.errors)  
        return super().form_invalid(form)


class ProductUpdateView(UpdateView):
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

class ProductVariantCreateView(CreateView):
    model = ProductVariant
    form_class = ProductVariantForm
    template_name = "products/variant_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.product = get_object_or_404(
            Product,
            pk=self.kwargs["product_pk"]
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.product = self.product
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["product"] = self.product
        context["page_title"] = "Add Product Variant"
        return context

    def get_success_url(self):
        return reverse_lazy(
            "products:detail",
            kwargs={"pk": self.product.pk}
        )

def supplier_update_view(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier updated successfully.')
            return redirect('products:supplier-list')
    else:
        form = SupplierForm(instance=supplier)
    
    return render(request, 'products/supplier_form.html', {'form': form, 'supplier': supplier})
@method_decorator(login_required, name='dispatch')
class StockAdjustmentView(View):
    """Handle manual stock adjustments and create StockMovement records"""
    
    def get(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        form = StockAdjustmentForm()
        
        # Get recent stock movements
        stock_movements = product.stock_movements.all()[:10]
        
        context = {
            'product': product,
            'form': form,
            'recent_movements': stock_movements,
        }
        return redirect(reverse('products:detail', args=[product.pk]))
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        form = StockAdjustmentForm(request.POST)
        
        if form.is_valid():
            adjustment_type = form.cleaned_data['adjustment_type']
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            
            # Map adjustment types to stock movement types
            movement_type_map = {
                'adjustment': 'adjustment',
                'purchase': 'purchase',
                'return': 'return',
                'damage': 'adjustment',  # damage treated as adjustment
            }
            
            # For purchases, returns, and damage - quantity is positive
            # For adjustments with negative qty, that means we're reducing stock
            movement_quantity = quantity if adjustment_type in ['purchase', 'return'] else quantity
            
            # Create stock movement
            StockMovement.objects.create(
                product=product,
                quantity=movement_quantity,
                movement_type=movement_type_map[adjustment_type],
                reference=f'Manual {adjustment_type}: {notes}' if notes else f'Manual {adjustment_type}'
            )
            
            messages.success(request, f'Stock adjusted successfully. Available stock: {product.available_stock}')
        else:
            messages.error(request, 'Please correct the errors below.')
        
        return redirect(reverse('products:detail', args=[product.pk]))


@method_decorator(login_required, name='dispatch')
class ExportProductsView(View):
    """Export products list to CSV or Excel"""
    
    def get(self, request):
        format_type = request.GET.get('format', 'csv')
        
        # Get queryset
        queryset = Product.objects.select_related('category', 'supplier', 'currency').order_by('name')
        
        # Define fields to export
        fields = [
            'sku',
            'name',
            'category__name',
            'supplier__name',
            'cost_price',
            'selling_price',
            'discount_percentage',
            'stock_quantity',
            'reorder_point',
            'unit',
            'is_active',
        ]
        
        # Generate filename
        filename = DataExporter.get_timestamp_filename('products_list')
        
        # Export based on format
        if format_type == 'excel':
            return DataExporter.export_to_excel(queryset, fields, filename, 'Products')
        else:
            return DataExporter.export_to_csv(queryset, fields, filename)


@method_decorator(login_required, name='dispatch')
class ExportCategoriesView(View):
    """Export categories list to CSV or Excel"""
    
    def get(self, request):
        format_type = request.GET.get('format', 'csv')
        
        queryset = Category.objects.all().order_by('name')
        fields = ['name', 'description', 'is_active', 'created_at']
        
        filename = DataExporter.get_timestamp_filename('categories_list')
        
        if format_type == 'excel':
            return DataExporter.export_to_excel(queryset, fields, filename, 'Categories')
        else:
            return DataExporter.export_to_csv(queryset, fields, filename)


@method_decorator(login_required, name='dispatch')
class ExportSuppliersView(View):
    """Export suppliers list to CSV or Excel"""
    
    def get(self, request):
        format_type = request.GET.get('format', 'csv')
        
        queryset = Supplier.objects.all().order_by('name')
        fields = ['name', 'contact_person', 'email', 'phone', 'address', 'is_active']
        
        filename = DataExporter.get_timestamp_filename('suppliers_list')
        
        if format_type == 'excel':
            return DataExporter.export_to_excel(queryset, fields, filename, 'Suppliers')
        else:
            return DataExporter.export_to_csv(queryset, fields, filename)