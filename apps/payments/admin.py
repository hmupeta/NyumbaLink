from django.contrib import admin
from .models import Wallet, CreditTransaction, ContactUnlock

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')

@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'transaction_type', 'amount', 'status', 'created_at')

@admin.register(ContactUnlock)
class ContactUnlockAdmin(admin.ModelAdmin):
    list_display = ('user', 'listing', 'created_at')
