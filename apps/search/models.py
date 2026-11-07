from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class SavedSearch(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches")
    name = models.CharField(max_length=128, help_text="e.g. Houses in Kabulonga")
    
    # Search criteria
    query = models.CharField(max_length=255, blank=True)
    transaction_type = models.CharField(max_length=16, blank=True)
    property_type = models.CharField(max_length=32, blank=True)
    province = models.CharField(max_length=64, blank=True)
    district = models.CharField(max_length=64, blank=True)
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ["-created_at"]
        verbose_name = "saved search"
        verbose_name_plural = "saved searches"

    def __str__(self):
        return f"{self.user.email} - {self.name}"
