from django.contrib import admin
from .models import LandlordPaymentSettings, PaymentTransaction

@admin.register(LandlordPaymentSettings)
class LandlordPaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ('landlord', 'stripe_onboarding_complete')

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'landlord', 'provider', 'amount', 'status', 'created_at')
