import uuid
from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel
from .enums import VerificationStatus, VerificationType

def verification_doc_path(instance, filename):
    return f"verifications/{instance.case.user_id}/{uuid.uuid4().hex}_{filename}"

class VerificationCase(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_cases")
    verification_type = models.CharField(max_length=32, choices=VerificationType.choices)
    status = models.CharField(max_length=16, choices=VerificationStatus.choices, default=VerificationStatus.PENDING)
    
    # Admin fields
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="verifications_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Internal admin notes")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "verification case"
        verbose_name_plural = "verification cases"
        constraints = [
            models.UniqueConstraint(fields=["user", "verification_type"], name="uniq_user_verification_type"),
        ]

    def __str__(self):
        return f"{self.get_verification_type_display()} - {self.user.email} ({self.status})"

class VerificationDocument(TimeStampedModel):
    case = models.ForeignKey(VerificationCase, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to=verification_doc_path)
    document_type = models.CharField(max_length=64, help_text="e.g. NRC Front, Title Deed, Utility Bill")
    
    class Meta(TimeStampedModel.Meta):
        verbose_name = "verification document"
        verbose_name_plural = "verification documents"
