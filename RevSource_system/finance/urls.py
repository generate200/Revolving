from django.urls import path
from .views import (
    FinanceOverviewView,
    AccountListView,
    AccountCreateView,
    CurrencyListView,
    CurrencyCreateView,
    CurrencyUpdateView,
    JournalEntryListView,
    JournalEntryCreateView,
    JournalEntryDetailView,
)

app_name = 'finance'

urlpatterns = [
    path('', FinanceOverviewView.as_view(), name='overview'),
    path('accounts/', AccountListView.as_view(), name='account-list'),
    path('accounts/add/', AccountCreateView.as_view(), name='account-create'),
    path('currencies/', CurrencyListView.as_view(), name='currency-list'),
    path('currencies/add/', CurrencyCreateView.as_view(), name='currency-create'),
    path('currencies/<int:pk>/edit/', CurrencyUpdateView.as_view(), name='currency-update'),
    path('journal/', JournalEntryListView.as_view(), name='journal-list'),
    path('journal/add/', JournalEntryCreateView.as_view(), name='journal-create'),
    path('journal/<int:pk>/', JournalEntryDetailView.as_view(), name='journal-detail'),
]
