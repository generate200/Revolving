#!/usr/bin/env python
"""
Script to create default currencies.
Run this after migrations with: python create_currencies.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RevSource_system.settings')
django.setup()

from finance.models import Currency

# Create default currencies
currencies = [
    {
        'code': 'USD',
        'name': 'US Dollar',
        'symbol': '$',
        'decimal_places': 2,
        'exchange_rate': '1.000000',
        'is_base': True,
        'is_active': True,
    },
    {
        'code': 'QAR',
        'name': 'Qatari Riyal',
        'symbol': 'ر.ق',
        'decimal_places': 2,
        'exchange_rate': '3.640000',
        'is_base': False,
        'is_active': True,
    },
    {
        'code': 'EUR',
        'name': 'Euro',
        'symbol': '€',
        'decimal_places': 2,
        'exchange_rate': '0.920000',
        'is_base': False,
        'is_active': True,
    },
    {
        'code': 'GBP',
        'name': 'British Pound',
        'symbol': '£',
        'decimal_places': 2,
        'exchange_rate': '0.790000',
        'is_base': False,
        'is_active': True,
    },
]

for curr_data in currencies:
    currency, created = Currency.objects.get_or_create(
        code=curr_data['code'],
        defaults=curr_data
    )
    status = "Created" if created else "Exists"
    print(f"{status}: {currency.code} - {currency.name} ({currency.symbol})")

print("\nDefault currencies setup complete!")
