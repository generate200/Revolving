from django.urls import path
from .views import (
    FinanceOverviewView,
    AccountListView,
    accounting_grouping,
    financial_reports,
    AccountCreateView,
    CurrencyListView,
    CurrencyCreateView,
    CurrencyUpdateView,
    JournalEntryListView,
    JournalEntryCreateView,
    JournalEntryDetailView,
    ExportjournalentriesView, 
    ExportAccountsView
)

app_name = 'finance'

urlpatterns = [
    path('', FinanceOverviewView.as_view(), name='overview'),
    path('accounts/', AccountListView.as_view(), name='account-list'),
    path('accounts/grouping/', accounting_grouping, name='account-grouping'),
    path('accounts/reports/', financial_reports, name='financial-reports'),
    path('accounts/add/', AccountCreateView.as_view(), name='account-create'),
    path('currencies/', CurrencyListView.as_view(), name='currency-list'),
    path('currencies/add/', CurrencyCreateView.as_view(), name='currency-create'),
    path('currencies/<int:pk>/edit/', CurrencyUpdateView.as_view(), name='currency-update'),
    path('journal/', JournalEntryListView.as_view(), name='journal-list'),
    path('journal/add/', JournalEntryCreateView.as_view(), name='journal-create'),
    path('journal/<int:pk>/', JournalEntryDetailView.as_view(), name='journal-detail'),
    path('export/', ExportjournalentriesView.as_view(), name='export-journal'),
    path('export/accounts/', ExportAccountsView.as_view(), name='account-export'),
]
