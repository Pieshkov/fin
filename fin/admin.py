from django.contrib import admin
from .models import Account, Category, Transaction

# Register your models here.

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'account_type', 'currency', 'balance', 'created_at')
    list_filter = ('account_type', 'currency')
    search_fields = ('name',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'created_at')
    list_filter = ('parent',)
    search_fields = ('name',)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'transaction_type', 'amount', 'currency', 'account', 'category')
    list_filter = ('transaction_type', 'currency', 'account', 'category')
    search_fields = ('comment',)
    date_hierarchy = 'date'
