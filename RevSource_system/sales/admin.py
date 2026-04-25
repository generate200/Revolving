from django.contrib import admin
from django.utils.html import format_html
from .models import Sale, SalesInvoice, SalesLine, Payment, StockMovement


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'total_price', 'date']
    list_filter = ['date', 'product']
    search_fields = ['product__name']
    readonly_fields = ['date']


class SalesLineInline(admin.TabularInline):
    model = SalesLine
    extra = 0
    readonly_fields = ['total_price']
    fields = ['product', 'variant', 'quantity', 'unit_price', 'discount', 'tax', 'total_price']


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['created_at']
    fields = ['method', 'amount', 'reference', 'created_at']


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'status_badge', 'total_amount', 'paid_amount', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['invoice_number', 'customer__name']
    readonly_fields = ['invoice_number', 'created_at', 'posted_at']
    
    inlines = [SalesLineInline, PaymentInline]
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'customer', 'currency', 'status', 'created_at', 'posted_at')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'discount_total', 'tax_total', 'total_amount', 'paid_amount', 'change_amount')
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': '#FFC107',
            'completed': '#28A745',
            'cancelled': '#DC3545',
            'refunded': '#17A2B8',
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(SalesLine)
class SalesLineAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product', 'quantity', 'unit_price', 'total_price']
    list_filter = ['invoice__created_at', 'product']
    search_fields = ['invoice__invoice_number', 'product__name']
    readonly_fields = ['total_price']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'method', 'amount', 'reference', 'created_at']
    list_filter = ['method', 'created_at']
    search_fields = ['invoice__invoice_number', 'reference']
    readonly_fields = ['created_at']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['reference', 'product', 'variant', 'movement_type_badge', 'quantity', 'created_at']
    list_filter = ['movement_type', 'created_at', 'product']
    search_fields = ['product__name', 'reference']
    readonly_fields = ['created_at', 'product_available_stock']
    
    def variant(self, obj):
        return obj.variant if obj.variant else "—"
    variant.short_description = 'Variant'
    
    def movement_type_badge(self, obj):
        colors = {
            'sale': '#DC3545',
            'purchase': '#28A745',
            'adjustment': '#FFC107',
            'return': '#17A2B8',
        }
        color = colors.get(obj.movement_type, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_movement_type_display()
        )
    movement_type_badge.short_description = 'Type'
    
    def product_available_stock(self, obj):
        return f"{obj.product.available_stock} units"
    product_available_stock.short_description = 'Current Available Stock'
