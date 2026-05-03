from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from products.models import Product, Supplier, Category
from finance.models import Currency, Account, JournalEntry, JournalLine
from accounts.models import User


class DashboardReportView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/report.html'
    
    def convert_currency(self, amount, selected_currency=None, base_currency=None):
        """Convert amount to selected currency using exchange rates."""
        if not amount:
            return Decimal('0.00')
        if not base_currency or not selected_currency:
            return amount
        if base_currency.exchange_rate <= 0 or selected_currency.exchange_rate <= 0:
            return amount
        rate = selected_currency.exchange_rate / base_currency.exchange_rate
        return amount * rate
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        currency_code = self.request.GET.get('currency')
        if currency_code:
            self.request.session['currency'] = currency_code
        currency_code = self.request.session.get('currency', 'QAR')
        selected_currency = Currency.objects.filter(code=currency_code, is_active=True).first()
        
        if not selected_currency:
            selected_currency = Currency.objects.filter(is_base=True).first()
        base_currency = Currency.objects.filter(is_base=True).first()
        
        context['selected_currency'] = selected_currency
        context['base_currency'] = base_currency
        context['currency_symbol'] = selected_currency.symbol if selected_currency else '$'
        context['convert_currency'] = self.convert_currency
        context['all_currencies'] = Currency.objects.filter(is_active=True)
        
        # Overview Metrics
        context['total_products'] = Product.objects.filter(is_active=True).count()
        context['total_suppliers'] = Supplier.objects.filter(is_active=True).count()
        context['total_currencies'] = Currency.objects.filter(is_active=True).count()
        
        # Stock Analysis
        low_stock_products = Product.objects.filter(
            Q(stock_quantity__lte=F('reorder_point')) & Q(is_active=True)
        )
        context['low_stock_count'] = low_stock_products.count()
        context['low_stock_products'] = low_stock_products[:10]
        
        # Total inventory value
        total_inventory = Product.objects.filter(is_active=True).aggregate(
            total_value=Coalesce(
                Sum(F('stock_quantity') * F('cost_price'), output_field=DecimalField()),
                Decimal('0.00')
            )
        )
        context['total_inventory_value'] = total_inventory['total_value']
        
        # Sales & Revenue Data
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        current_month_start = today.replace(day=1)
        
        # Revenue entries (from JournalLine lines)
        revenue_accounts = Account.objects.filter(type='revenue')
        
        # Today's revenue
        today_revenue = JournalLine.objects.filter(
            account__in=revenue_accounts,
            journal__date=today,
            journal__posted=True
        ).aggregate(
            revenue=Coalesce(Sum('credit'), Decimal('0.00'))
        )['revenue']
        context['today_revenue'] = today_revenue
        
        # Monthly revenue
        monthly_revenue = JournalLine.objects.filter(
            account__in=revenue_accounts,
            journal__date__gte=current_month_start,
            journal__posted=True
        ).aggregate(
            revenue=Coalesce(Sum('credit'), Decimal('0.00'))
        )['revenue']
        context['monthly_revenue'] = monthly_revenue
        
        # Last 30 days revenue
        last_30_revenue = JournalLine.objects.filter(
            account__in=revenue_accounts,
            journal__date__gte=last_30_days,
            journal__posted=True
        ).aggregate(
            revenue=Coalesce(Sum('credit'), Decimal('0.00'))
        )['revenue']
        context['last_30_revenue'] = last_30_revenue
        
        # Expenses
        expense_accounts = Account.objects.filter(type='expense')
        monthly_expenses = JournalLine.objects.filter(
            account__in=expense_accounts,
            journal__date__gte=current_month_start,
            journal__posted=True
        ).aggregate(
            expenses=Coalesce(Sum('debit'), Decimal('0.00'))
        )['expenses']
        context['monthly_expenses'] = monthly_expenses
        context['net_income'] = monthly_revenue - monthly_expenses
        
        # Top selling products (by sold quantity estimate via journal entries)
        top_products = Product.objects.filter(is_active=True).annotate(
            stock_value=F('selling_price') * F('stock_quantity')
        ).order_by('-stock_value')[:5]
        context['top_products'] = top_products
        
        # Fast-moving items (low stock but has reorder point set = in demand)
        fast_moving = Product.objects.filter(
            is_active=True,
            reorder_point__gt=0,
            stock_quantity__lte=20
        ).order_by('-selling_price')[:5]
        context['fast_moving_items'] = fast_moving
        
        # Recent journal entries (as orders/transactions)
        recent_entries = JournalEntry.objects.filter(
            posted=True
        ).order_by('-date')[:10]
        context['recent_transactions'] = recent_entries
        
        # Account Balances for cash flow
        accounts_data = Account.objects.filter(
            is_active=True
        ).exclude(
            type__in=['revenue', 'expense']
        )
        context['accounts'] = accounts_data
        
        # Asset total
        asset_balance = Account.objects.filter(
            type='asset',
            is_active=True
        ).aggregate(
            total=Coalesce(Sum('balance'), Decimal('0.00'))
        )['total']
        context['asset_balance'] = asset_balance
        
        # Liability total
        liability_balance = Account.objects.filter(
            type='liability',
            is_active=True
        ).aggregate(
            total=Coalesce(Sum('balance'), Decimal('0.00'))
        )['total']
        context['liability_balance'] = liability_balance
        
        # Convert all financial values to selected currency
        context['converted_total_inventory_value'] = self.convert_currency(context['total_inventory_value'], selected_currency, base_currency)
        context['converted_today_revenue'] = self.convert_currency(context['today_revenue'], selected_currency, base_currency)
        context['converted_monthly_revenue'] = self.convert_currency(context['monthly_revenue'], selected_currency, base_currency)
        context['converted_last_30_revenue'] = self.convert_currency(context['last_30_revenue'], selected_currency, base_currency)
        context['converted_monthly_expenses'] = self.convert_currency(context['monthly_expenses'], selected_currency, base_currency)
        context['converted_net_income'] = self.convert_currency(context['net_income'], selected_currency, base_currency)
        context['converted_asset_balance'] = self.convert_currency(context['asset_balance'], selected_currency, base_currency)
        context['converted_liability_balance'] = self.convert_currency(context['liability_balance'], selected_currency, base_currency)
        context['converted_equity'] = context['converted_asset_balance'] - context['converted_liability_balance']
        
        # Product categories
        categories = Category.objects.filter(
            is_active=True
        ).annotate(
            product_count=Count('product')
        )
        context['categories'] = categories
        
        return context
