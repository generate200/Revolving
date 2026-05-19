from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DetailView, FormView, View
from django.contrib import messages
from django.db.models import Sum, Q
from django.http import HttpResponse
from decimal import Decimal
from .models import (
    Account,
    JournalEntry,
    JournalLine,
    Currency,
    SubAccountCategory,
    normalize_natural_balance,
    generate_trial_balance,
    generate_financial_statements,
)
from .forms import JournalEntryForm, JournalLineFormSet, AccountForm, CurrencyForm, SubAccountCategoryForm
from finance.utils.currency import CurrencyService
from django.utils.decorators import method_decorator
from core.exporters import DataExporter
from django.contrib.auth.decorators import login_required
from collections import OrderedDict



def check_duplicate_account(code=None, name=None):
    """Helper function to check for duplicate accounts."""
    duplicates = []
    
    if code:
        code = code.strip().upper()
        existing = Account.objects.filter(code__iexact=code).first()
        if existing:
            duplicates.append({
                'type': 'code',
                'value': code,
                'account': existing,
                'message': f"Account code '{code}' already exists"
            })
    
    if name:
        name = name.strip()
        existing = Account.objects.filter(name__iexact=name).first()
        if existing:
            duplicates.append({
                'type': 'name',
                'value': name,
                'account': existing,
                'message': f"Account name '{name}' already exists"
            })
    
    return duplicates


class FinanceOverviewView(TemplateView):
    template_name = 'finance/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_currency = _get_active_currency(self.request)
        currency_service = CurrencyService(self.request, selected_currency=selected_currency)

        type_totals = {
            'asset': Decimal('0.00'),
            'liability': Decimal('0.00'),
            'equity': Decimal('0.00'),
            'revenue': Decimal('0.00'),
            'expense': Decimal('0.00'),
        }

        for account in Account.objects.filter(is_active=True):
            amount = account.get_balance_in_currency(selected_currency)
            type_totals[account.type] += amount

        context['total_assets'] = type_totals['asset']
        context['total_liabilities'] = type_totals['liability']
        context['total_equity'] = type_totals['equity'] + type_totals['revenue'] - type_totals['expense']
        context['currency_symbol'] = selected_currency.symbol if selected_currency else '$'
        context['selected_currency'] = selected_currency
        context['currencies'] = Currency.objects.filter(is_active=True)
        context['dashboard_cards'] = [
            {
                'title': 'Journal entries',
                'description': 'Create and post journal entries to update account balances.',
                'url': reverse_lazy('finance:journal-list')
            },
            {
                'title': 'Chart of accounts',
                'description': 'View all accounts, balances, and account types.',
                'url': reverse_lazy('finance:account-list')
            },
            {
                'title': 'Currencies',
                'description': 'Manage currencies and exchange rates for multi-currency transactions.',
                'url': reverse_lazy('finance:currency-list')
            },
            {
                'title': 'Financial reports',
                'description': 'View balance sheet, income statement, and trial balance.',
                'url': reverse_lazy('finance:financial-reports')
            },
        ]

        recent_entries = JournalEntry.objects.all().order_by('-date')[:10]
        for entry in recent_entries:
            entry.converted_debit = currency_service.convert(
                entry.get_total_debit(),
                from_currency=entry.currency,
                to_currency=selected_currency
            )
            entry.converted_credit = currency_service.convert(
                entry.get_total_credit(),
                from_currency=entry.currency,
                to_currency=selected_currency
            )

        context['recent_entries'] = recent_entries
        return context
    
ACCOUNT_TYPE_ORDER = [
    ('asset', 'Assets'),
    ('liability', 'Liabilities'),
    ('equity', 'Equity'),
    ('revenue', 'Revenue'),
    ('expense', 'Expenses'),
]
def accounting_grouping(request):
    """Group accounts by type with proper currency conversion."""
    
    grouped = OrderedDict()

    # --- Currency selection (EXACT same logic as AccountListView) ---
    currency_code = request.GET.get('currency')

    if currency_code:
        request.session['currency'] = currency_code
    currency_code = request.session.get('currency', 'QAR')

    selected_currency = (
        Currency.objects.filter(code=currency_code).first()
        if currency_code
        else Currency.objects.filter(is_base=True).first()
    )

    base_currency = Currency.objects.filter(is_base=True).first()

    if not selected_currency:
        selected_currency = base_currency

    # Use CurrencyService for proper conversion
    currency_service = CurrencyService(request, selected_currency=selected_currency)

    # --- Conversion helper using new service ---
    def convert(amount):
        # Since we're dealing with account balances that are in base currency,
        # we convert from base to selected
        return currency_service.convert_from_base(amount, selected_currency)

    # Get all active accounts
    accounts = Account.objects.filter(is_active=True).order_by('code')

    # Create groups
    for type_code, type_name in ACCOUNT_TYPE_ORDER:

        type_accounts = accounts.filter(type=type_code)

        total = Decimal('0.00')

        for account in type_accounts:
            # Convert balance from base currency to selected currency
            account.converted_balance = convert(account.balance)
            total += account.converted_balance

        grouped[type_name] = {
            'accounts': type_accounts,
            'total': total.quantize(Decimal('0.01'))
        }

    return render(
        request,
        'finance/account_grouping.html',
        {
            'grouped': grouped,
            'selected_currency': selected_currency,
            'currencies': Currency.objects.filter(is_active=True),
            'currency_symbol': selected_currency.symbol if selected_currency else '?',
        }
    )


def _get_active_currency(request):
    currency_code = request.GET.get('currency') or request.session.get('currency')
    selected_currency = None

    if currency_code:
        selected_currency = Currency.objects.filter(code=currency_code, is_active=True).first()
        if selected_currency:
            request.session['currency'] = selected_currency.code

    if not selected_currency:
        selected_currency = Currency.objects.filter(is_active=True, is_base=False).first()

    if not selected_currency:
        selected_currency = Currency.objects.filter(is_base=True).first()

    return selected_currency


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def financial_reports(request):
    selected_currency = _get_active_currency(request)
    currency_service = CurrencyService(request, selected_currency=selected_currency)

    start_date = _parse_date(request.GET.get('start_date'))
    end_date = _parse_date(request.GET.get('end_date'))

    journal_lines = JournalLine.objects.filter(journal__posted=True).select_related('journal', 'account')
    if start_date:
        journal_lines = journal_lines.filter(journal__date__gte=start_date)
    if end_date:
        journal_lines = journal_lines.filter(journal__date__lte=end_date)

    report_totals = {
        'asset': Decimal('0.00'),
        'liability': Decimal('0.00'),
        'equity': Decimal('0.00'),
        'revenue': Decimal('0.00'),
        'expense': Decimal('0.00'),
    }

    account_totals = {}
    for line in journal_lines:
        account = line.account
        if not account or not account.type:
            continue

        debit = currency_service.convert(
            line.debit,
            from_currency=line.journal.currency,
            to_currency=selected_currency,
        )
        credit = currency_service.convert(
            line.credit,
            from_currency=line.journal.currency,
            to_currency=selected_currency,
        )

        normalized = normalize_natural_balance(account.type, debit - credit)

        if account.type not in report_totals:
            continue

        report_totals[account.type] += normalized
        account_totals.setdefault(account.code, {
            'account': account,
            'type': account.type,
            'subcategory': account.subcategory.name if account.subcategory else None,
            'amount': Decimal('0.00'),
        })
        account_totals[account.code]['amount'] += normalized

    balance_sheet = {
        'assets': report_totals['asset'],
        'liabilities': report_totals['liability'],
        'equity': report_totals['equity'],
    }
    income_statement = {
        'revenue': report_totals['revenue'],
        'expense': report_totals['expense'],
    }

    net_income = income_statement['revenue'] - income_statement['expense']
    total_equity = balance_sheet['equity'] + net_income
    balance_sheet_balanced = balance_sheet['assets'] == (balance_sheet['liabilities'] + total_equity)

    trial_balance = generate_trial_balance(target_currency=selected_currency)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="financial_report.csv"'
        response.write('Account Code,Account Name,Type,Subcategory,Amount\n')
        for account_data in trial_balance['accounts']:
            response.write(
                f"{account_data['code']},{account_data['name']},{account_data['type']},{account_data['subcategory'] or ''},"
                f"{account_data['debit'] - account_data['credit']}\n"
            )
        return response

    return render(request, 'finance/financial_statements.html', {
        'selected_currency': selected_currency,
        'currencies': Currency.objects.filter(is_active=True),
        'currency_symbol': selected_currency.symbol if selected_currency else '?',
        'start_date': start_date,
        'end_date': end_date,
        'balance_sheet': {
            **balance_sheet,
            'net_income': net_income,
            'total_equity_including_net_income': total_equity,
            'balanced': balance_sheet_balanced,
        },
        'income_statement': income_statement,
        'net_income': net_income,
        'trial_balance': trial_balance,
        'account_totals': account_totals.values(),
    })

class AccountListView(ListView):
    model = Account
    template_name = 'finance/account_list.html'
    context_object_name = 'accounts'
    paginate_by = 25

    def get_queryset(self):
        return Account.objects.order_by('code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # --- Currency selection ---
        currency_code = self.request.GET.get('currency')

        if currency_code:
            self.request.session['currency'] = currency_code
        currency_code = self.request.session.get('currency', 'USD')

        selected_currency = (
            Currency.objects.filter(code=currency_code).first()
            if currency_code
            else Currency.objects.filter(is_base=True).first()
        )

        base_currency = Currency.objects.filter(is_base=True).first()

        if not selected_currency:
            selected_currency = base_currency

        # Use CurrencyService for proper conversion
        currency_service = CurrencyService(self.request, selected_currency=selected_currency)

        # --- Conversion helper using new service ---
        def convert(amount):
            # Since we're dealing with account balances that are in base currency,
            # we convert from base to selected
            return currency_service.convert_from_base(amount, selected_currency)

        # --- Totals ---
        total_assets = Account.objects.filter(type='asset').aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0.00')

        total_liabilities = Account.objects.filter(type='liability').aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0.00')

        equity_accounts = Account.objects.filter(type='equity').aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0.00')

        revenue_accounts = Account.objects.filter(type='revenue').aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0.00')

        expense_accounts = Account.objects.filter(type='expense').aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0.00')

        total_equity = equity_accounts + revenue_accounts - expense_accounts

        context['total_assets'] = convert(total_assets)
        context['total_liabilities'] = convert(total_liabilities)
        context['total_equity'] = convert(total_equity)

        # --- Convert account balances ---
        for acc in context['accounts']:
            acc.converted_balance = convert(acc.balance)

        # --- Currency UI context ---
        context['currencies'] = Currency.objects.filter(is_active=True)
        context['selected_currency'] = selected_currency
        context['currency_symbol'] = selected_currency.symbol

        return context



class AccountCreateView(CreateView):
    """Create a new account with duplicate prevention and inline sub-account category creation."""
    model = Account
    form_class = AccountForm
    template_name = 'finance/account_form.html'
    success_url = reverse_lazy('finance:account-list')

    def get_initial(self):
        """Populate initial form data if provided via GET."""
        initial = super().get_initial()
        if 'code' in self.request.GET:
            initial['code'] = self.request.GET['code']
        if 'name' in self.request.GET:
            initial['name'] = self.request.GET['name']
        return initial

    def post(self, request, *args, **kwargs):
        if 'create_subcategory' in request.POST:
            subcategory_form = SubAccountCategoryForm(request.POST)
            if subcategory_form.is_valid():
                category = subcategory_form.save()
                messages.success(request, f"✓ Sub-account category '{category.name}' created.")
                return redirect('finance:account-create')
            
            form = self.get_form()
            return self.render_to_response(self.get_context_data(form=form, subcategory_form=subcategory_form))

        form = self.get_form()
        if form.is_valid():
            account = form.save()
            messages.success(
                request,
                f"✓ Account {account.code} ({account.name}) created successfully."
            )
            return redirect('finance:account-list')
        
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        """Add duplicate check suggestions and subcategory creation context."""
        context = super().get_context_data(**kwargs)
        context.setdefault('subcategory_form', SubAccountCategoryForm())
        context['subcategories'] = SubAccountCategory.objects.order_by('name')

        # Check for potential duplicates if form has been submitted with errors
        if self.request.POST and 'create_subcategory' not in self.request.POST:
            code = self.request.POST.get('code')
            name = self.request.POST.get('name')
            duplicates = check_duplicate_account(code=code, name=name)
            if duplicates:
                context['duplicates'] = duplicates
                for dup in duplicates:
                    messages.warning(
                        self.request,
                        f"⚠ {dup['message']} - {dup['account'].code}: {dup['account'].name}"
                    )
        return context


class CurrencyListView(ListView):
    model = Currency
    template_name = 'finance/currency_list.html'
    context_object_name = 'currencies'
    paginate_by = 25

    def get_queryset(self):
        return Currency.objects.order_by('code')


class CurrencyCreateView(CreateView):
    model = Currency
    form_class = CurrencyForm
    template_name = 'finance/currency_form.html'
    success_url = reverse_lazy('finance:currency-list')

    def form_valid(self, form):
        currency = form.save()
        messages.success(self.request, f"Currency {currency.code} ({currency.name}) created successfully.")
        return super().form_valid(form)


class CurrencyUpdateView(UpdateView):
    model = Currency
    form_class = CurrencyForm
    template_name = 'finance/currency_form.html'
    success_url = reverse_lazy('finance:currency-list')

    def form_valid(self, form):
        currency = form.save()
        messages.success(self.request, f"Currency {currency.code} ({currency.name}) updated successfully.")
        return super().form_valid(form)


class JournalEntryListView(ListView):
    model = JournalEntry
    template_name = 'finance/journal_entry_list.html'
    context_object_name = 'entries'
    paginate_by = 20

    def get_queryset(self):
        return JournalEntry.objects.order_by('-date', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        currency_service = CurrencyService(self.request)
        entries = context.get('entries') or []

        for entry in entries:
            entry.converted_debit = currency_service.convert(
                entry.get_total_debit(),
                from_currency=entry.currency,
                to_currency=currency_service.selected_currency
            )
            entry.converted_credit = currency_service.convert(
                entry.get_total_credit(),
                from_currency=entry.currency,
                to_currency=currency_service.selected_currency
            )

        context.update(currency_service.context())
        return context


class JournalEntryCreateView(FormView):
    template_name = 'finance/journal_entry_form.html'
    form_class = JournalEntryForm
    success_url = reverse_lazy('finance:journal-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = JournalLineFormSet(self.request.POST)
        else:
            context['formset'] = JournalLineFormSet()
        context['accounts'] = Account.objects.filter(is_active=True)
        context['currencies'] = Currency.objects.filter(is_active=True)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            # Save the journal entry first to get the primary key
            journal_entry = form.save(commit=False)
            if not journal_entry.currency:
                journal_entry.currency = Currency.objects.filter(is_base=True).first()
            if not journal_entry.exchange_rate or journal_entry.exchange_rate == Decimal('0.000000'):
                journal_entry.exchange_rate = journal_entry.currency.exchange_rate
            
            journal_entry.save()
            
            # Now save each line with the journal entry reference
            for line_form in formset:
                if line_form.cleaned_data and not line_form.cleaned_data.get('DELETE', False):
                    line = line_form.save(commit=False)
                    line.journal = journal_entry
                    line.save()
            
            # Now validate the complete journal entry
            try:
                if journal_entry.lines.count() < 2:
                    journal_entry.delete()  # Clean up
                    messages.error(self.request, "Journal entry must have at least 2 lines (debit and credit).")
                    return self.form_invalid(form)
                
                if not journal_entry.is_balanced():
                    journal_entry.delete()  # Clean up
                    messages.error(self.request, 
                        f"Journal entry is not balanced. Total Debit: {journal_entry.get_total_debit()}, "
                        f"Total Credit: {journal_entry.get_total_credit()}")
                    return self.form_invalid(form)
                
                # Automatically post the entry to update account balances
                journal_entry.post()
                messages.success(self.request, f"Journal Entry {journal_entry.id} created and posted successfully. Account balances updated.")
                
            except Exception as e:
                journal_entry.delete()  # Clean up on any error
                messages.error(self.request, f"Error creating journal entry: {str(e)}")
                return self.form_invalid(form)
            
            return redirect('finance:journal-list')
        else:
            return self.form_invalid(form)


class JournalEntryDetailView(DetailView):
    model = JournalEntry
    template_name = 'finance/journal_entry_detail.html'
    context_object_name = 'entry'

    def post(self, request, *args, **kwargs):
        entry = self.get_object()
        action = request.POST.get('action')
        
        if action == 'post' and not entry.posted:
            try:
                entry.post()
                messages.success(request, f"Journal Entry {entry.id} posted successfully. Account balances updated.")
            except Exception as e:
                messages.error(request, f"Error posting entry: {str(e)}")
            return redirect('finance:journal-detail', pk=entry.id)
        
        elif action == 'reverse' and entry.posted:
            try:
                reversal = entry.reverse()
                messages.success(request, f"Journal Entry {entry.id} reversed. Created reversal entry {reversal.id}.")
            except Exception as e:
                messages.error(request, f"Error reversing entry: {str(e)}")
            return redirect('finance:journal-detail', pk=entry.id)
        
        return self.get(request, *args, **kwargs)
    
@method_decorator(login_required, name='dispatch') 
class ExportjournalentriesView(View):
    """Export journal entries to CSV or Excel"""

    def get(self, request):
        format_type = request.GET.get('format', 'csv')

        queryset = JournalLine.objects.select_related('journal', 'account').order_by('-journal__date')
        fields = [
            'journal__id',
            'journal__date',
            'journal__description',
            'account__code',
            'account__name',
            'debit',
            'credit',
        ]

        filename = DataExporter.get_timestamp_filename('journal_entries')

        if format_type == 'excel':
            return DataExporter.export_to_excel(queryset, fields, filename, 'Journal Entries')
        else:
            return DataExporter.export_to_csv(queryset, fields, filename)
        
@method_decorator(login_required, name='dispatch')    
class ExportAccountsView(View):
    """Export accounts to CSV or Excel"""

    def get(self, request):
        format_type = request.GET.get('format', 'csv')

        queryset = Account.objects.order_by('code')
        fields = [
            'code',
            'name',
            'type',
            'balance',
        ]

        filename = DataExporter.get_timestamp_filename('accounts')

        if format_type == 'excel':
            return DataExporter.export_to_excel(queryset, fields, filename, 'Accounts')
        else:
            return DataExporter.export_to_csv(queryset, fields, filename)