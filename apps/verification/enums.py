from django.db import models

class VerificationType(models.TextChoices):
    IDENTITY = "IDENTITY", "Identity Verification"
    OWNERSHIP_AUTHORITY = "OWNERSHIP_AUTHORITY", "Ownership / Authority"
    PROPERTY_PHYSICAL = "PROPERTY_PHYSICAL", "Physical Property Check"

class VerificationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING = "PENDING", "Pending Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
