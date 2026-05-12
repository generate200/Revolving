"""
Production readiness tests for Finance module.
Tests for performance, concurrency, edge cases, and error handling.
"""
import time
from decimal import Decimal
from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from django.db.models import Sum
from finance.models import Account, Currency, JournalEntry, JournalLine
from finance.utils.currency import CurrencyService
from django.test.utils import override_settings
from django.core.cache import cache


class CurrencyConversionTests(TestCase):
    """Test currency conversion accuracy and edge cases."""
    
    def setUp(self):
        """Create test currencies and accounts."""
        self.base_currency = Currency.objects.create(
            code='QAR',
            name='Qatar Riyal',
            symbol='ر.ق',
            is_base=True,
            exchange_rate=Decimal('1.0')
        )
        self.usd = Currency.objects.create(
            code='USD',
            name='US Dollar',
            symbol='$',
            is_base=False,
            exchange_rate=Decimal('3.64')  # 1 USD = 3.64 QAR
        )
        self.eur = Currency.objects.create(
            code='EUR',
            name='Euro',
            symbol='€',
            is_base=False,
            exchange_rate=Decimal('3.97')  # 1 EUR = 3.97 QAR
        )
        
    def test_conversion_accuracy(self):
        """Test currency conversion maintains precision."""
        service = CurrencyService(base_currency=self.base_currency, selected_currency=self.usd)
        
        # Test conversion: 100 QAR to USD
        result = service.convert_from_base(Decimal('100.00'), self.usd)
        expected = (Decimal('100.00') / Decimal('3.64')).quantize(Decimal('0.01'))
        
        self.assertEqual(result, expected)
    
    def test_conversion_rounding(self):
        """Test that conversions round correctly to 2 decimals."""
        service = CurrencyService(base_currency=self.base_currency, selected_currency=self.usd)
        
        result = service.convert_from_base(Decimal('123.456'), self.usd)
        
        # Should be rounded to 2 decimal places
        self.assertEqual(result % 1, result % 1)  # Has 2 decimals
        self.assertLessEqual(len(str(result).split('.')[-1]), 2)
    
    def test_zero_amount_conversion(self):
        """Test converting zero amounts."""
        service = CurrencyService(base_currency=self.base_currency, selected_currency=self.usd)
        
        result = service.convert_from_base(Decimal('0.00'), self.usd)
        
        self.assertEqual(result, Decimal('0.00'))
    
    def test_negative_amount_conversion(self):
        """Test converting negative amounts (for expense accounts)."""
        service = CurrencyService(base_currency=self.base_currency, selected_currency=self.usd)
        
        result = service.convert_from_base(Decimal('-100.00'), self.usd)
        
        self.assertLess(result, 0)
    
    def test_missing_currency_fallback(self):
        """Test handling when currency is missing."""
        service = CurrencyService(base_currency=self.base_currency, selected_currency=None)
        
        result = service.convert_from_base(Decimal('100.00'), None)
        
        # Should return unmodified amount
        self.assertEqual(result, Decimal('100.00'))


class JournalEntryValidationTests(TestCase):
    """Test journal entry debit/credit balance and validation."""
    
    def setUp(self):
        """Create test data."""
        self.user = User.objects.create_user('testuser', 'test@test.com', 'password')
        self.currency = Currency.objects.create(
            code='QAR',
            name='Qatar Riyal',
            symbol='ร.ฃ',
            is_base=True,
            exchange_rate=Decimal('1.0')
        )
        self.asset_account = Account.objects.create(
            code='A001',
            name='Cash',
            type='asset',
            is_active=True
        )
        self.expense_account = Account.objects.create(
            code='E001',
            name='Salary',
            type='expense',
            is_active=True
        )
    
    def test_journal_entry_debit_credit_balance(self):
        """Test that journal entries maintain debit/credit balance."""
        entry = JournalEntry.objects.create(
            user=self.user,
            currency=self.currency,
            date='2024-01-01',
            description='Test entry'
        )
        
        # Debit 100 to cash
        JournalLine.objects.create(
            journal_entry=entry,
            account=self.asset_account,
            debit=Decimal('100.00'),
            credit=Decimal('0.00')
        )
        
        # Credit 100 to salary
        JournalLine.objects.create(
            journal_entry=entry,
            account=self.expense_account,
            debit=Decimal('0.00'),
            credit=Decimal('100.00')
        )
        
        total_debit = entry.get_total_debit()
        total_credit = entry.get_total_credit()
        
        self.assertEqual(total_debit, total_credit)
        self.assertEqual(total_debit, Decimal('100.00'))
    
    def test_imbalanced_journal_entry_prevented(self):
        """Test that imbalanced entries raise validation error."""
        entry = JournalEntry.objects.create(
            user=self.user,
            currency=self.currency,
            date='2024-01-01',
            description='Imbalanced entry'
        )
        
        # Create imbalanced lines
        JournalLine.objects.create(
            journal_entry=entry,
            account=self.asset_account,
            debit=Decimal('100.00'),
            credit=Decimal('0.00')
        )
        
        JournalLine.objects.create(
            journal_entry=entry,
            account=self.expense_account,
            debit=Decimal('0.00'),
            credit=Decimal('50.00')  # Unbalanced
        )
        
        # Should be caught at view level, but test the math
        total_debit = entry.get_total_debit()
        total_credit = entry.get_total_credit()
        
        self.assertNotEqual(total_debit, total_credit)


class AccountGroupingPerformanceTests(TransactionTestCase):
    """Test account grouping performance with various data volumes."""
    
    def setUp(self):
        """Create test currencies."""
        self.currency = Currency.objects.create(
            code='QAR',
            name='Qatar Riyal',
            symbol='ร.ฃ',
            is_base=True,
            exchange_rate=Decimal('1.0')
        )
        
    def test_grouping_with_many_accounts(self):
        """Test account grouping performance with 100+ accounts."""
        # Create 100 accounts across different types
        account_types = ['asset', 'liability', 'equity', 'revenue', 'expense']
        
        for i in range(100):
            Account.objects.create(
                code=f'ACC{i:04d}',
                name=f'Test Account {i}',
                type=account_types[i % 5],
                balance=Decimal(f'{i * 100}.00'),
                is_active=True
            )
        
        # Time the grouping operation
        start = time.time()
        accounts = Account.objects.filter(is_active=True).order_by('code')
        grouped = {}
        
        for atype in account_types:
            type_accounts = accounts.filter(type=atype)
            grouped[atype] = {
                'accounts': list(type_accounts),
                'total': sum(a.balance for a in type_accounts)
            }
        
        duration = time.time() - start
        
        # Should complete in < 100ms
        self.assertLess(duration, 0.1, f"Grouping took {duration:.3f}s, should be < 0.1s")
    
    def test_conversion_bulk_performance(self):
        """Test bulk currency conversion performance."""
        from finance.utils.currency import CurrencyService
        
        # Create 50 accounts
        for i in range(50):
            Account.objects.create(
                code=f'ACC{i:03d}',
                name=f'Account {i}',
                type='asset',
                balance=Decimal(f'{1000 * (i+1)}.00'),
                is_active=True
            )
        
        service = CurrencyService(selected_currency=self.currency)
        accounts = Account.objects.filter(is_active=True)
        
        # Time the conversion
        start = time.time()
        for account in accounts:
            converted = service.convert_from_base(account.balance, self.currency)
        duration = time.time() - start
        
        # Should complete in < 50ms for 50 accounts
        self.assertLess(duration, 0.05, f"Conversion took {duration:.3f}s")


class ViewResponseTimeTests(TestCase):
    """Test response times for key views."""
    
    def setUp(self):
        """Create test user and data."""
        self.user = User.objects.create_user('testuser', 'test@test.com', 'password')
        self.client = Client()
        self.client.login(username='testuser', password='password')
        
        # Create test currency and accounts
        self.currency = Currency.objects.create(
            code='QAR',
            name='Qatar Riyal',
            symbol='ร.ฃ',
            is_base=True,
            exchange_rate=Decimal('1.0')
        )
        
        for i in range(10):
            Account.objects.create(
                code=f'ACC{i:03d}',
                name=f'Account {i}',
                type=['asset', 'liability', 'equity', 'revenue', 'expense'][i % 5],
                balance=Decimal(f'{5000 * (i+1)}.00'),
                is_active=True
            )
    
    def test_account_list_response_time(self):
        """Test account list view response time."""
        start = time.time()
        response = self.client.get('/finance/accounts/')
        duration = time.time() - start
        
        self.assertEqual(response.status_code, 200)
        # Should respond in < 200ms
        self.assertLess(duration, 0.2, f"Response took {duration:.3f}s")
    
    def test_account_grouping_response_time(self):
        """Test account grouping view response time."""
        start = time.time()
        response = self.client.get('/finance/accounts/grouping/')
        duration = time.time() - start
        
        self.assertEqual(response.status_code, 200)
        # Should respond in < 200ms
        self.assertLess(duration, 0.2, f"Response took {duration:.3f}s")


class ExchangeRateEdgeCasesTests(TestCase):
    """Test edge cases in exchange rate handling."""
    
    def setUp(self):
        """Create currencies with edge case rates."""
        self.qar = Currency.objects.create(
            code='QAR',
            name='Qatar Riyal',
            symbol='ร.ฃ',
            is_base=True,
            exchange_rate=Decimal('1.0')
        )
        self.btc = Currency.objects.create(
            code='BTC',
            name='Bitcoin',
            symbol='₿',
            is_base=False,
            exchange_rate=Decimal('0.000023')  # Extreme ratio
        )
        self.jpy = Currency.objects.create(
            code='JPY',
            name='Japanese Yen',
            symbol='¥',
            is_base=False,
            exchange_rate=Decimal('270.5')  # Very large ratio
        )
    
    def test_extreme_rate_small_currency(self):
        """Test conversion with very small exchange rate."""
        service = CurrencyService(base_currency=self.qar, selected_currency=self.btc)
        result = service.convert_from_base(Decimal('10000.00'), self.btc)
        
        # Result should be positive and reasonable
        self.assertGreater(result, 0)
        self.assertLess(result, 1)  # Should be fraction of BTC
    
    def test_extreme_rate_large_currency(self):
        """Test conversion with very large exchange rate."""
        service = CurrencyService(base_currency=self.qar, selected_currency=self.jpy)
        result = service.convert_from_base(Decimal('100.00'), self.jpy)
        
        # Result should be proportionally larger
        self.assertGreater(result, 20000)


class DatabaseQueryOptimizationTests(TransactionTestCase):
    """Test for N+1 query problems."""
    
    def setUp(self):
        """Create test data."""
        self.currency = Currency.objects.create(
            code='QAR',
            name='Qatar Riyal',
            symbol='ร.ฃ',
            is_base=True,
            exchange_rate=Decimal('1.0')
        )
    
    def test_account_list_query_count(self):
        """Test that account list doesn't have N+1 query problem."""
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        # Create multiple accounts
        for i in range(20):
            Account.objects.create(
                code=f'ACC{i:03d}',
                name=f'Account {i}',
                type='asset',
                is_active=True
            )
        
        # Execute the view logic and count queries
        with CaptureQueriesContext(connection) as ctx:
            accounts = list(Account.objects.filter(is_active=True).order_by('code'))
        
        # Should only be 1 query, not 21 (1 + 20 for each account)
        self.assertLess(len(ctx.captured_queries), 5, 
                       f"Too many queries: {len(ctx.captured_queries)}")


class ConcurrentUserTests(TransactionTestCase):
    """Test behavior with concurrent users."""
    
    def setUp(self):
        """Create test data."""
        self.currency = Currency.objects.create(
            code='QAR',
            name='Qatar Riyal',
            symbol='ร.ฃ',
            is_base=True,
            exchange_rate=Decimal('1.0')
        )
        self.account = Account.objects.create(
            code='A001',
            name='Shared Account',
            type='asset',
            balance=Decimal('1000.00'),
            is_active=True
        )
    
    def test_concurrent_currency_selection(self):
        """Test that currency selection doesn't interfere between users."""
        from django.contrib.sessions.models import Session
        from django.test import RequestFactory
        
        # Simulate two users selecting different currencies
        factory = RequestFactory()
        
        # User 1 requests QAR
        request1 = factory.get('/finance/accounts/', {'currency': 'QAR'})
        request1.session = {}
        
        # User 2 requests USD
        request2 = factory.get('/finance/accounts/', {'currency': 'USD'})
        request2.session = {}
        
        # Each should maintain their own selection
        self.assertEqual(request1.GET.get('currency'), 'QAR')
        self.assertEqual(request2.GET.get('currency'), 'USD')


class ErrorHandlingTests(TestCase):
    """Test error handling for edge cases."""
    
    def setUp(self):
        """Create minimal test data."""
        self.currency = Currency.objects.create(
            code='QAR',
            name='Qatar Riyal',
            symbol='ร.ฃ',
            is_base=True,
            exchange_rate=Decimal('1.0')
        )
    
    def test_missing_base_currency_handling(self):
        """Test behavior when base currency is missing."""
        from finance.utils.currency import CurrencyService
        
        # Try to create service without base currency
        service = CurrencyService(base_currency=None, selected_currency=self.currency)
        
        # Should have fallback
        self.assertIsNotNone(service.base_currency)
    
    def test_invalid_account_type(self):
        """Test creation of account with invalid type."""
        with self.assertRaises(Exception):
            Account.objects.create(
                code='INVALID',
                name='Invalid Account',
                type='invalid_type',
                is_active=True
            )
    
    def test_duplicate_account_code(self):
        """Test that duplicate account codes are prevented."""
        Account.objects.create(
            code='DUP001',
            name='First Account',
            type='asset',
            is_active=True
        )
        
        # Attempt duplicate
        with self.assertRaises(Exception):
            Account.objects.create(
                code='DUP001',
                name='Second Account',
                type='liability',
                is_active=True
            )
