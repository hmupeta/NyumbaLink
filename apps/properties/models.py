import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel
from apps.locations.models import Neighbourhood

from .enums import (
    ListingStatus,
    MediaType,
    PricePeriod,
    PropertyStatus,
    PropertyType,
    ReportReason,
    ReportStatus,
    TransactionType,
)


def listing_media_path(instance, filename):
    return f"listings/{instance.listing_id}/{uuid.uuid4().hex}_{filename}"


class PropertyFeature(TimeStampedModel):
    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=64, unique=True)
    category = models.CharField(max_length=32, blank=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "property feature"
        verbose_name_plural = "property features"

    def __str__(self):
        return self.name


class Property(TimeStampedModel):
    neighbourhood = models.ForeignKey(
        Neighbourhood, on_delete=models.PROTECT, related_name="properties"
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="properties_submitted",
    )
    property_type = models.CharField(max_length=32, choices=PropertyType.choices)
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    bathrooms = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    floor_area = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Square metres",
    )
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    address_line = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=PropertyStatus.choices, default=PropertyStatus.ACTIVE
    )
    features = models.ManyToManyField(PropertyFeature, blank=True, related_name="properties")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "property"
        verbose_name_plural = "properties"
        indexes = [
            models.Index(fields=["neighbourhood", "status"]),
            models.Index(fields=["submitted_by"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(latitude__isnull=True, longitude__isnull=True)
                    | Q(latitude__isnull=False, longitude__isnull=False)
                ),
                name="property_both_coords_or_neither",
            ),
        ]

    def __str__(self):
        return f"{self.property_type} in {self.neighbourhood.name}"


class PropertyAuthority(TimeStampedModel):
    """Grants a user permission to act on behalf of a property's submitter.

    Exists so an agent can create listings on a landlord's property without
    becoming the property's owner. Revocable and optionally time-limited.
    """

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="authorities"
    )
    granted_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_authorities",
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authorities_granted",
    )
    can_list = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "property authority"
        verbose_name_plural = "property authorities"
        constraints = [
            models.UniqueConstraint(
                fields=["property", "granted_to"],
                name="uniq_authority_property_user",
            ),
        ]

    def is_active(self) -> bool:
        from django.utils import timezone

        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at <= timezone.now():
            return False
        return True

    def __str__(self):
        return f"{self.granted_to} on {self.property_id}"


class Listing(TimeStampedModel):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="listings")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="listings_created",
    )
    transaction_type = models.CharField(max_length=16, choices=TransactionType.choices)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZMW")
    price_period = models.CharField(
        max_length=8, choices=PricePeriod.choices, default=PricePeriod.MONTH
    )
    deposit_months = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    available_from = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=ListingStatus.choices, default=ListingStatus.DRAFT
    )
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    moderation_note = models.TextField(blank=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "listing"
        verbose_name_plural = "listings"
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["transaction_type", "status"]),
            models.Index(fields=["price"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(price__gte=0), name="listing_price_non_negative"),
        ]

    def __str__(self):
        return self.title or f"Listing {self.id}"


class ListingMedia(TimeStampedModel):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to=listing_media_path)
    media_type = models.CharField(max_length=8, choices=MediaType.choices)
    caption = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "listing media"
        verbose_name_plural = "listing media"
        ordering = ["display_order", "created_at"]
        indexes = [models.Index(fields=["listing", "display_order"])]


class Report(TimeStampedModel):
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_filed",
    )
    target_listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, null=True, blank=True, related_name="reports"
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reports_against",
    )
    reason = models.CharField(max_length=16, choices=ReportReason.choices)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=ReportStatus.choices, default=ReportStatus.OPEN
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "report"
        verbose_name_plural = "reports"
        indexes = [models.Index(fields=["status", "-created_at"])]
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(target_listing__isnull=False, target_user__isnull=True)
                    | Q(target_listing__isnull=True, target_user__isnull=False)
                ),
                name="report_exactly_one_target",
            ),
        ]


class AuditLog(models.Model):
    """Append-only record of moderation and state changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=32)
    target_id = models.UUIDField()
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "audit log"
        verbose_name_plural = "audit logs"
        indexes = [models.Index(fields=["target_type", "target_id"])]

    def __str__(self):
        return f"{self.action} {self.target_type}/{self.target_id}"
