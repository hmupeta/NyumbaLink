import uuid
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class LandlordPaymentSettings(TimeStampedModel):
    """Stores encrypted provider credentials per landlord/agency."""
    landlord = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_settings"
    )
    
    # Stripe Connect
    stripe_connected_account_id = models.CharField(max_length=64, blank=True)
    stripe_onboarding_complete = models.BooleanField(default=False)
    
    # PayPal
    paypal_client_id = models.CharField(max_length=128, blank=True)
    paypal_client_secret = models.CharField(max_length=256, blank=True)
    paypal_merchant_id = models.CharField(max_length=64, blank=True)
    
    # MTN MoMo (encrypted)
    mtn_api_user = models.CharField(max_length=128, blank=True)
    mtn_api_key = models.CharField(max_length=256, blank=True)
    mtn_subscription_key = models.CharField(max_length=256, blank=True)
    mtn_target_environment = models.CharField(max_length=32, default="mtnzambia")
    
    # Airtel Money (encrypted)
    airtel_client_id = models.CharField(max_length=128, blank=True)
    airtel_client_secret = models.CharField(max_length=256, blank=True)
    
    # Zamtel Kwacha
    zamtel_merchant_id = models.CharField(max_length=64, blank=True)
    zamtel_api_key = models.CharField(max_length=256, blank=True)
    zamtel_api_base_url = models.URLField(default="https://api.zamtel.com/kwacha")
    
    class Meta(TimeStampedModel.Meta):
        verbose_name = "landlord payment settings"
        verbose_name_plural = "landlord payment settings"

    def __str__(self):
        return f"Payment settings for {self.landlord.email}"

class PaymentTransaction(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_transactions"
    )
    listing = models.ForeignKey(
        "properties.Listing", on_delete=models.SET_NULL, null=True, blank=True
    )
    provider = models.CharField(max_length=16)  # MTN, AIRTEL, ZAMTEL, STRIPE, PAYPAL
    reference = models.CharField(max_length=128, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZMW")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    provider_transaction_id = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ["-created_at"]
