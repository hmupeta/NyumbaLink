from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class Notification(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=128)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, help_text="Frontend URL to redirect to")
    is_read = models.BooleanField(default=False)

    class Meta(TimeStampedModel.Meta):
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.title}"
