
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class Wallet(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.PositiveIntegerField(default=0, help_text="Credits available")

    def __str__(self):
        return f"{self.user.email} - {self.balance} credits"

class CreditTransaction(TimeStampedModel):
    class Type(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase Credits"
        UNLOCK = "UNLOCK", "Unlock Contact"
        REFUND = "REFUND", "Refund"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=16, choices=Type.choices)
    amount = models.IntegerField(help_text="Positive for credits added, negative for spent")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reference = models.CharField(max_length=64, blank=True, help_text="PSP Reference ID")
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.transaction_type} ({self.amount}) - {self.wallet.user.email}"

class ContactUnlock(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="unlocked_contacts")
    listing = models.ForeignKey("properties.Listing", on_delete=models.CASCADE, related_name="unlocks")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="uniq_user_listing_unlock"),
        ]

    def __str__(self):
        return f"{self.user.email} unlocked {self.listing.title}"
