from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class Review(TimeStampedModel):
    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_received")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_given")
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()

    class Meta(TimeStampedModel.Meta):
        constraints = [
            # A user can only review a landlord once
            models.UniqueConstraint(fields=["landlord", "reviewer"], name="uniq_landlord_reviewer"),
        ]

    def __str__(self):
        return f"{self.rating}★ for {self.landlord.email} by {self.reviewer.email}"
