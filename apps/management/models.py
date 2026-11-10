from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from apps.properties.models import Property

class Lease(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ENDED = "ENDED", "Ended"

    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leases")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="leases")
    
    tenant_name = models.CharField(max_length=128)
    tenant_phone = models.CharField(max_length=20)
    tenant_email = models.EmailField(blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=12, decimal_places=2)
    deposit_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    
    # Agreement & Signature Tracking
    agreement_text = models.TextField(blank=True, help_text="Generated legal lease agreement")
    landlord_signed = models.BooleanField(default=False)
    tenant_signed = models.BooleanField(default=False)
    landlord_signed_at = models.DateTimeField(null=True, blank=True)
    tenant_signed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.tenant_name} @ {self.property.neighbourhood.name}"

class RentRecord(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        OVERDUE = "OVERDUE", "Overdue"

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name="rent_records")
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["-due_date"]

    def __str__(self):
        return f"{self.lease.tenant_name} - {self.due_date.strftime('%b %Y')} ({self.status})"
