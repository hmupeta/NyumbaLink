from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from apps.properties.models import Property
from apps.management.models import Lease

class MaintenanceRequest(TimeStampedModel):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High / Urgent"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"

    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="maintenance_requests")
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="maintenance_requests")
    lease = models.ForeignKey(Lease, on_delete=models.SET_NULL, null=True, blank=True, help_text="Optional: Link to specific tenant")
    
    title = models.CharField(max_length=128)
    description = models.TextField()
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ["-created_at"]
        verbose_name = "maintenance request"
        verbose_name_plural = "maintenance requests"

    def __str__(self):
        return f"{self.title} - {self.property.neighbourhood.name} ({self.status})"
