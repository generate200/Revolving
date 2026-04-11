from django.contrib import admin
from .models import Account, JournalEntry, JournalLine, Currency


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol', 'exchange_rate', 'is_base', 'is_active')
    list_filter = ('is_base', 'is_active')
    search_fields = ('code', 'name')
    readonly_fields = ('created_at',) if hasattr(Currency, 'created_at') else ()
    fieldsets = (
        ('Currency Info', {'fields': ('code', 'name', 'symbol', 'decimal_places')}),
        ('Exchange', {'fields': ('exchange_rate', 'is_base')}),
        ('Status', {'fields': ('is_active',)}),
    )


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'type', 'balance', 'is_active')
    list_filter = ('type', 'is_active')
    search_fields = ('code', 'name')
    readonly_fields = ('balance', 'created_at', 'updated_at')
    fieldsets = (
        ('General', {'fields': ('code', 'name', 'type')}),
        ('Description', {'fields': ('description',)}),
        ('Balance', {'fields': ('balance',)}),
        ('Status', {'fields': ('is_active',)}),
        ('Metadata', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 1
    fields = ('account', 'debit', 'credit', 'comment')
    readonly_fields = ()


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'currency', 'description', 'posted', 'get_total_debit', 'get_total_credit')
    list_filter = ('posted', 'date', 'currency')
    search_fields = ('description', 'memo')
    readonly_fields = ('created_at', 'updated_at', 'get_total_debit', 'get_total_credit', 'posted')
    date_hierarchy = 'date'
    inlines = [JournalLineInline]
    fieldsets = (
        ('Entry Info', {'fields': ('date', 'description', 'memo', 'created_by')}),
        ('Currency', {'fields': ('currency', 'exchange_rate')}),
        ('Status', {'fields': ('posted',)}),
        ('Totals', {'fields': ('get_total_debit', 'get_total_credit')}),
        ('Metadata', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def get_total_debit(self, obj):
        return obj.get_total_debit()
    get_total_debit.short_description = 'Total Debit'

    def get_total_credit(self, obj):
        return obj.get_total_credit()
    get_total_credit.short_description = 'Total Credit'
