from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, CreateView, DetailView, FormView
from django.contrib import messages
from django.db.models import Sum, Q
from decimal import Decimal 
from .models import Account, JournalEntry, JournalLine  ,Currency
from .forms import JournalEntryForm, JournalLineFormSet, AccountForm, CurrencyForm


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
        context['assets'] = Account.objects.filter(type='asset')
        context['total_assets'] = Account.objects.filter(type='asset').aggregate(
            Sum('balance')
        )['balance__sum'] or Decimal('0.00')
        context['recent_entries'] = JournalEntry.objects.all()[:10]
        return context


class AccountListView(ListView):
    model = Account
    template_name = 'finance/account_list.html'
    context_object_name = 'accounts'
    paginate_by = 25

    def get_queryset(self):
        return Account.objects.order_by('code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_assets'] = Account.objects.filter(type='asset').aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0.00')
        context['total_liabilities'] = Account.objects.filter(type='liability').aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0.00')
        context['total_equity'] = Account.objects.filter(type='equity').aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0.00')
        return context


class AccountCreateView(CreateView):
    """Create a new account with duplicate prevention."""
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
        form = self.get_form()
        
        if form.is_valid():
            account = form.save()
            messages.success(
                request,
                f"✓ Account {account.code} ({account.name}) created successfully."
            )
            return redirect('finance:account-list')
        
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add duplicate check suggestions to context."""
        context = super().get_context_data(**kwargs)
        
        # Check for potential duplicates if form has been submitted with errors
        if self.request.POST:
            code = self.request.POST.get('code')
            name = self.request.POST.get('name')
            
            duplicates = check_duplicate_account(code=code, name=name)
            if duplicates:
                context['duplicates'] = duplicates
                
                # Suggest the existing account
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


class CurrencyUpdateView(CreateView):
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
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        
        if formset.is_valid():
            # Save the journal entry first to get the primary key
            journal_entry = form.save()
            
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
