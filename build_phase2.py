#!/usr/bin/env python3
"""NyumbaLink Phase 2 scaffold: properties, listings, moderation, permissions.

Usage:
    python build_phase2.py             # write files, patch existing, print runbook
    python build_phase2.py --force     # overwrite existing files
    python build_phase2.py --check     # also run manage.py check afterwards
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------- properties app

PROPERTIES_INIT = ""

PROPERTIES_APPS = '''
from django.apps import AppConfig


class PropertiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.properties"
    label = "properties"
'''.strip() + "\n"

PROPERTIES_ENUMS = '''
from django.db import models


class PropertyType(models.TextChoices):
    HOUSE = "HOUSE", "House"
    APARTMENT = "APARTMENT", "Apartment"
    FLAT = "FLAT", "Flat"
    TOWNHOUSE = "TOWNHOUSE", "Townhouse"
    BOARDING_HOUSE = "BOARDING_HOUSE", "Boarding house"
    STUDENT_LODGE = "STUDENT_LODGE", "Student lodge"
    COMMERCIAL = "COMMERCIAL", "Commercial"
    LAND = "LAND", "Land"
    OTHER = "OTHER", "Other"


class TransactionType(models.TextChoices):
    RENT = "RENT", "For rent"
    SALE = "SALE", "For sale"
    SHORT_LET = "SHORT_LET", "Short let"


class PricePeriod(models.TextChoices):
    MONTH = "MONTH", "Per month"
    YEAR = "YEAR", "Per year"
    ONCE = "ONCE", "One-off"


class PropertyStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class ListingStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted for review"
    PUBLISHED = "PUBLISHED", "Published"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    EXPIRED = "EXPIRED", "Expired"
    ARCHIVED = "ARCHIVED", "Archived"


class MediaType(models.TextChoices):
    IMAGE = "IMAGE", "Image"
    VIDEO = "VIDEO", "Video"
    TOUR = "TOUR", "Virtual tour"


class ReportReason(models.TextChoices):
    FRAUD = "FRAUD", "Fraud or scam"
    DUPLICATE = "DUPLICATE", "Duplicate listing"
    WRONG_INFO = "WRONG_INFO", "Inaccurate information"
    UNAVAILABLE = "UNAVAILABLE", "Property no longer available"
    OFFENSIVE = "OFFENSIVE", "Offensive content"
    OTHER = "OTHER", "Other"


class ReportStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    REVIEWING = "REVIEWING", "In review"
    RESOLVED = "RESOLVED", "Resolved"
    DISMISSED = "DISMISSED", "Dismissed"
'''.strip() + "\n"

PROPERTIES_MODELS = '''
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
'''.strip() + "\n"

PROPERTIES_PERMISSIONS = '''
from django.db.models import Q
from django.utils import timezone

from .models import Listing, Property, PropertyAuthority


def user_is_moderator(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def user_can_manage_property(user, prop: Property) -> bool:
    if user_is_moderator(user):
        return True
    return prop.submitted_by_id == user.id


def user_can_create_listing(user, prop: Property) -> bool:
    """A listing may be created by the property submitter, a moderator,
    or a user holding a live PropertyAuthority with can_list=True."""
    if user_is_moderator(user):
        return True
    if prop.submitted_by_id == user.id:
        return True
    return PropertyAuthority.objects.filter(
        property=prop,
        granted_to=user,
        can_list=True,
        revoked_at__isnull=True,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    ).exists()


def user_can_edit_listing(user, listing: Listing) -> bool:
    """The advertiser may edit their own listing. The property submitter may
    also edit it — this is how an owner withdraws an agent's advertisement."""
    if user_is_moderator(user):
        return True
    if listing.created_by_id == user.id:
        return True
    return listing.property.submitted_by_id == user.id


def user_can_view_listing(user, listing: Listing) -> bool:
    from .enums import ListingStatus

    if listing.status == ListingStatus.PUBLISHED:
        return True
    if not user or not user.is_authenticated:
        return False
    return user_can_edit_listing(user, listing)
'''.strip() + "\n"

PROPERTIES_SERVICES = '''
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from .enums import ListingStatus
from .models import AuditLog, Listing
from .permissions import user_can_edit_listing, user_is_moderator


class ListingTransitionError(Exception):
    pass


def _audit(actor, action, listing, **payload):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type="Listing",
        target_id=listing.id,
        payload=payload,
    )


def _transition(listing, from_states, to_state, *, actor, note=""):
    if listing.status not in from_states:
        raise ListingTransitionError(
            f"Cannot move listing from {listing.status} to {to_state}"
        )
    listing.status = to_state
    if note:
        listing.moderation_note = note
    return listing


@transaction.atomic
def submit_listing(listing: Listing, *, actor) -> Listing:
    if not user_can_edit_listing(actor, listing):
        raise PermissionDenied("You cannot submit this listing")
    _transition(listing, {ListingStatus.DRAFT}, ListingStatus.SUBMITTED, actor=actor)
    listing.save(update_fields=["status", "moderation_note", "updated_at"])
    _audit(actor, "listing.submitted", listing)
    return listing


@transaction.atomic
def publish_listing(listing: Listing, *, actor, note="") -> Listing:
    if not user_is_moderator(actor):
        raise PermissionDenied("Only moderators can publish listings")
    _transition(listing, {ListingStatus.SUBMITTED}, ListingStatus.PUBLISHED, actor=actor, note=note)
    listing.published_at = timezone.now()
    listing.save(update_fields=["status", "published_at", "moderation_note", "updated_at"])
    _audit(actor, "listing.published", listing, note=note)
    return listing


@transaction.atomic
def reject_listing(listing: Listing, *, actor, reason: str) -> Listing:
    if not user_is_moderator(actor):
        raise PermissionDenied("Only moderators can reject listings")
    if not reason:
        raise ListingTransitionError("A rejection reason is required")
    _transition(listing, {ListingStatus.SUBMITTED}, ListingStatus.REJECTED, actor=actor, note=reason)
    listing.rejection_reason = reason
    listing.save(update_fields=["status", "rejection_reason", "moderation_note", "updated_at"])
    _audit(actor, "listing.rejected", listing, reason=reason)
    return listing


@transaction.atomic
def withdraw_listing(listing: Listing, *, actor) -> Listing:
    if not user_can_edit_listing(actor, listing):
        raise PermissionDenied("You cannot withdraw this listing")
    _transition(
        listing,
        {ListingStatus.PUBLISHED, ListingStatus.REJECTED},
        ListingStatus.WITHDRAWN,
        actor=actor,
    )
    listing.save(update_fields=["status", "updated_at"])
    _audit(actor, "listing.withdrawn", listing)
    return listing


@transaction.atomic
def archive_listing(listing: Listing, *, actor) -> Listing:
    if not user_can_edit_listing(actor, listing):
        raise PermissionDenied("You cannot archive this listing")
    _transition(
        listing,
        {ListingStatus.PUBLISHED, ListingStatus.REJECTED, ListingStatus.WITHDRAWN, ListingStatus.EXPIRED},
        ListingStatus.ARCHIVED,
        actor=actor,
    )
    listing.save(update_fields=["status", "updated_at"])
    _audit(actor, "listing.archived", listing)
    return listing
'''.strip() + "\n"

PROPERTIES_SERIALIZERS = '''
from rest_framework import serializers

from .enums import ListingStatus
from .models import Listing, ListingMedia, Property, PropertyFeature
from .permissions import user_can_create_listing


class PropertyFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyFeature
        fields = ("id", "name", "slug", "category")


class ListingMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingMedia
        fields = ("id", "listing", "file", "media_type", "caption", "display_order")
        read_only_fields = ("id", "listing")


class PropertySerializer(serializers.ModelSerializer):
    features = PropertyFeatureSerializer(many=True, read_only=True)
    feature_slugs = serializers.ListField(
        child=serializers.SlugField(), write_only=True, required=False
    )
    neighbourhood_name = serializers.CharField(source="neighbourhood.name", read_only=True)
    submitted_by_email = serializers.CharField(source="submitted_by.email", read_only=True)

    class Meta:
        model = Property
        fields = (
            "id", "neighbourhood", "neighbourhood_name", "submitted_by",
            "submitted_by_email", "property_type", "bedrooms", "bathrooms",
            "floor_area", "latitude", "longitude", "address_line",
            "description", "status", "features", "feature_slugs",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "submitted_by", "status", "created_at", "updated_at")

    def _apply_features(self, prop, slugs):
        if slugs is None:
            return
        features = PropertyFeature.objects.filter(slug__in=slugs)
        prop.features.set(features)

    def create(self, validated_data):
        slugs = validated_data.pop("feature_slugs", None)
        prop = Property.objects.create(**validated_data)
        self._apply_features(prop, slugs)
        return prop

    def update(self, instance, validated_data):
        slugs = validated_data.pop("feature_slugs", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        self._apply_features(instance, slugs)
        return instance


class ListingSerializer(serializers.ModelSerializer):
    media = ListingMediaSerializer(many=True, read_only=True)
    property_summary = serializers.SerializerMethodField()
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = Listing
        fields = (
            "id", "property", "property_summary", "created_by", "created_by_email",
            "transaction_type", "price", "currency", "price_period",
            "deposit_months", "title", "description", "available_from",
            "status", "published_at", "expires_at", "rejection_reason",
            "moderation_note", "media", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "created_by", "status", "published_at", "expires_at",
            "rejection_reason", "moderation_note", "created_at", "updated_at",
        )

    def get_property_summary(self, obj):
        p = obj.property
        return {
            "id": str(p.id),
            "property_type": p.property_type,
            "bedrooms": p.bedrooms,
            "bathrooms": str(p.bathrooms) if p.bathrooms is not None else None,
            "neighbourhood": p.neighbourhood.name,
        }

    def validate(self, attrs):
        request = self.context.get("request")
        prop = attrs.get("property") or getattr(self.instance, "property", None)
        if self.instance is None and request and prop:
            if not user_can_create_listing(request.user, prop):
                raise serializers.ValidationError(
                    {"property": "You do not have authority to list this property."}
                )
        return attrs


class ListingActionSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import Report
        model = Report
        fields = (
            "id", "reporter", "target_listing", "target_user", "reason",
            "description", "status", "resolved_by", "resolved_at",
            "resolution_note", "created_at",
        )
        read_only_fields = (
            "id", "reporter", "status", "resolved_by", "resolved_at", "created_at",
        )

    def validate(self, attrs):
        listing = attrs.get("target_listing")
        user = attrs.get("target_user")
        if bool(listing) == bool(user):
            raise serializers.ValidationError(
                "Provide exactly one of target_listing or target_user."
            )
        return attrs
'''.strip() + "\n"

PROPERTIES_VIEWS = '''
from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .enums import ListingStatus
from .models import Listing, ListingMedia, Property, Report
from .permissions import user_can_edit_listing, user_can_manage_property, user_is_moderator
from .serializers import (
    ListingActionSerializer,
    ListingMediaSerializer,
    ListingSerializer,
    PropertySerializer,
    ReportSerializer,
)
from . import services


class IsOwnerOrModerator(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if isinstance(obj, Property):
            return user_can_manage_property(request.user, obj)
        if isinstance(obj, Listing):
            return user_can_edit_listing(request.user, obj)
        return False


class PropertyViewSet(viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrModerator)
    filterset_fields = ("property_type", "neighbourhood", "status")
    search_fields = ("description", "address_line")
    ordering_fields = ("created_at",)

    def get_queryset(self):
        qs = Property.objects.select_related(
            "neighbourhood__locality__district__province", "submitted_by"
        ).prefetch_related("features")
        if self.request.user.is_authenticated:
            qs = qs.filter(Q(status="ACTIVE") | Q(submitted_by=self.request.user))
        else:
            qs = qs.filter(status="ACTIVE")
        return qs

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user)


class ListingFilter(filters.FilterSet):
    province = filters.CharFilter(field_name="property__neighbourhood__locality__district__province__slug")
    district = filters.CharFilter(field_name="property__neighbourhood__locality__district__slug")
    locality = filters.CharFilter(field_name="property__neighbourhood__locality__slug")
    neighbourhood = filters.CharFilter(field_name="property__neighbourhood__slug")
    property_type = filters.CharFilter(field_name="property__property_type")
    features = filters.CharFilter(method="filter_features")
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    min_bedrooms = filters.NumberFilter(field_name="property__bedrooms", lookup_expr="gte")

    class Meta:
        model = Listing
        fields = ("transaction_type", "currency", "price_period")

    def filter_features(self, qs, name, value):
        slugs = [s for s in value.split(",") if s]
        return qs.filter(property__features__slug__in=slugs).distinct()


class ListingViewSet(viewsets.ModelViewSet):
    serializer_class = ListingSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, IsOwnerOrModerator)
    filterset_class = ListingFilter
    search_fields = ("title", "description")
    ordering_fields = ("price", "published_at", "created_at")
    ordering = ("-published_at", "-created_at")

    def get_queryset(self):
        qs = Listing.objects.select_related(
            "property__neighbourhood__locality__district__province",
            "created_by",
        ).prefetch_related("media")
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(
                Q(status=ListingStatus.PUBLISHED)
                | Q(created_by=user)
                | Q(property__submitted_by=user)
            )
        return qs.filter(status=ListingStatus.PUBLISHED)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def _transition_action(self, request, fn, **kwargs):
        listing = self.get_object()
        body = ListingActionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            fn(listing, actor=request.user, **body.validated_data, **kwargs)
        except services.ListingTransitionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ListingSerializer(listing, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return self._transition_action(request, services.submit_listing)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        return self._transition_action(request, services.publish_listing)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition_action(request, services.reject_listing)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        return self._transition_action(request, services.withdraw_listing)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._transition_action(request, services.archive_listing)


class ListingMediaViewSet(viewsets.ModelViewSet):
    serializer_class = ListingMediaSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ListingMedia.objects.filter(
            listing_id=self.kwargs["listing_pk"]
        ).select_related("listing")

    def perform_create(self, serializer):
        listing = Listing.objects.get(pk=self.kwargs["listing_pk"])
        if not user_can_edit_listing(self.request.user, listing):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot add media to this listing")
        serializer.save(listing=listing)


class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Report.objects.select_related("reporter", "target_listing", "target_user")
        if user_is_moderator(self.request.user):
            return qs
        return qs.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        if not user_is_moderator(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only moderators can update reports")
        return super().partial_update(request, *args, **kwargs)
'''.strip() + "\n"

PROPERTIES_URLS = '''
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers

from .views import ListingMediaViewSet, ListingViewSet, PropertyViewSet, ReportViewSet

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="property")
router.register("listings", ListingViewSet, basename="listing")
router.register("reports", ReportViewSet, basename="report")

listing_router = nested_routers.NestedDefaultRouter(router, "listings", lookup="listing")
listing_router.register("media", ListingMediaViewSet, basename="listing-media")

urlpatterns = router.urls + listing_router.urls
'''.strip() + "\n"

PROPERTIES_ADMIN = '''
from django.contrib import admin

from .models import AuditLog, Listing, ListingMedia, Property, PropertyAuthority, PropertyFeature, Report


class ListingMediaInline(admin.TabularInline):
    model = ListingMedia
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("id", "property_type", "neighbourhood", "submitted_by", "status", "created_at")
    list_filter = ("property_type", "status", "neighbourhood__locality__district__province")
    search_fields = ("address_line", "description", "submitted_by__email")
    readonly_fields = ("id", "created_at", "updated_at")
    filter_horizontal = ("features",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "transaction_type", "price", "currency", "status", "published_at")
    list_filter = ("status", "transaction_type", "currency")
    search_fields = ("title", "description", "created_by__email")
    readonly_fields = ("id", "published_at", "created_at", "updated_at")
    inlines = [ListingMediaInline]
    actions = ["publish_listings"]

    @admin.action(description="Publish selected submitted listings")
    def publish_listings(self, request, queryset):
        from . import services
        n = 0
        for listing in queryset.filter(status="SUBMITTED"):
            services.publish_listing(listing, actor=request.user)
            n += 1
        self.message_user(request, f"Published {n} listing(s).")


@admin.register(PropertyAuthority)
class PropertyAuthorityAdmin(admin.ModelAdmin):
    list_display = ("property", "granted_to", "granted_by", "can_list", "expires_at", "revoked_at")
    list_filter = ("can_list", "can_edit")
    search_fields = ("property__id", "granted_to__email")


@admin.register(PropertyFeature)
class PropertyFeatureAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "reason", "status", "reporter", "target_listing", "target_user", "created_at")
    list_filter = ("status", "reason")
    search_fields = ("description", "reporter__email")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "target_type", "target_id", "actor")
    list_filter = ("action", "target_type")
    search_fields = ("target_id",)
    readonly_fields = ("id", "created_at", "actor", "action", "target_type", "target_id", "payload")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
'''.strip() + "\n"

SEED_FEATURES = '''
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.properties.models import PropertyFeature

FEATURES = [
    ("Parking", "parking"), ("Garage", "parking"),
    ("Borehole", "utilities"), ("Municipal water", "utilities"),
    ("Solar backup", "utilities"), ("Generator", "utilities"),
    ("ZESCO power", "utilities"), ("Fibre internet", "utilities"),
    ("Swimming pool", "amenities"), ("Gym", "amenities"),
    ("Garden", "amenities"), ("Balcony", "amenities"),
    ("Furnished", "amenities"), ("Air conditioning", "amenities"),
    ("Security guard", "security"), ("Electric fence", "security"),
    ("Gated community", "security"), ("CCTV", "security"),
    ("Pet friendly", "policy"), ("Wheelchair accessible", "policy"),
]


class Command(BaseCommand):
    help = "Seed common property features."

    def handle(self, *args, **options):
        created = 0
        for name, category in FEATURES:
            _, was_created = PropertyFeature.objects.get_or_create(
                slug=slugify(name), defaults={"name": name, "category": category}
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} new features."))
'''.strip() + "\n"

TEST_FACTORIES = '''
from django.contrib.auth import get_user_model

from apps.locations.models import District, Locality, Neighbourhood, Province
from apps.properties.enums import PropertyType, TransactionType
from apps.properties.models import Listing, Property

User = get_user_model()


def make_location():
    province, _ = Province.objects.get_or_create(slug="lusaka", defaults={"name": "Lusaka", "code": "LS"})
    district, _ = District.objects.get_or_create(province=province, slug="lusaka", defaults={"name": "Lusaka"})
    locality, _ = Locality.objects.get_or_create(district=district, slug="lusaka", defaults={"name": "Lusaka"})
    hood, _ = Neighbourhood.objects.get_or_create(locality=locality, slug="kabulonga", defaults={"name": "Kabulonga"})
    return hood


def make_user(email="landlord@example.com", password="pw", **kw):
    return User.objects.create_user(email=email, password=password, **kw)


def make_property(submitter, **kw):
    hood = make_location()
    defaults = dict(
        neighbourhood=hood,
        submitted_by=submitter,
        property_type=PropertyType.HOUSE,
        bedrooms=3,
        bathrooms=2,
        latitude="-15.423456",
        longitude="28.321234",
    )
    defaults.update(kw)
    return Property.objects.create(**defaults)


def make_listing(prop, creator, **kw):
    defaults = dict(
        property=prop,
        created_by=creator,
        transaction_type=TransactionType.RENT,
        price="5000.00",
        currency="ZMW",
        title="3-bed house in Kabulonga",
    )
    defaults.update(kw)
    return Listing.objects.create(**defaults)
'''.strip() + "\n"

TEST_PERMISSIONS = '''
from django.test import TestCase

from apps.properties.enums import ListingStatus
from apps.properties.models import PropertyAuthority
from apps.properties.permissions import (
    user_can_create_listing,
    user_can_edit_listing,
    user_can_manage_property,
)

from .factories import make_listing, make_property, make_user


class PermissionMatrixTests(TestCase):
    def setUp(self):
        self.landlord = make_user("landlord@x.com")
        self.agent = make_user("agent@x.com")
        self.other = make_user("other@x.com")
        self.staff = make_user("staff@x.com", is_staff=True)
        self.prop = make_property(self.landlord)

    def test_landlord_can_manage_own_property(self):
        self.assertTrue(user_can_manage_property(self.landlord, self.prop))

    def test_other_cannot_manage_property(self):
        self.assertFalse(user_can_manage_property(self.other, self.prop))

    def test_landlord_can_create_listing(self):
        self.assertTrue(user_can_create_listing(self.landlord, self.prop))

    def test_agent_without_authority_cannot_create_listing(self):
        self.assertFalse(user_can_create_listing(self.agent, self.prop))

    def test_agent_with_authority_can_create_listing(self):
        PropertyAuthority.objects.create(
            property=self.prop, granted_to=self.agent, granted_by=self.landlord
        )
        self.assertTrue(user_can_create_listing(self.agent, self.prop))

    def test_revoked_authority_blocks_agent(self):
        from django.utils import timezone
        PropertyAuthority.objects.create(
            property=self.prop, granted_to=self.agent, granted_by=self.landlord,
            revoked_at=timezone.now(),
        )
        self.assertFalse(user_can_create_listing(self.agent, self.prop))

    def test_landlord_can_edit_agent_listing(self):
        PropertyAuthority.objects.create(
            property=self.prop, granted_to=self.agent, granted_by=self.landlord
        )
        listing = make_listing(self.prop, self.agent)
        self.assertTrue(user_can_edit_listing(self.landlord, listing))

    def test_staff_bypasses(self):
        listing = make_listing(self.prop, self.landlord)
        self.assertTrue(user_can_edit_listing(self.staff, listing))
        self.assertTrue(user_can_create_listing(self.staff, self.prop))
'''.strip() + "\n"

TEST_WORKFLOW = '''
from django.test import TestCase

from apps.properties import services
from apps.properties.enums import ListingStatus
from apps.properties.models import AuditLog

from .factories import make_listing, make_property, make_user


class ListingWorkflowTests(TestCase):
    def setUp(self):
        self.landlord = make_user("l@x.com")
        self.staff = make_user("s@x.com", is_staff=True)
        self.prop = make_property(self.landlord)
        self.listing = make_listing(self.prop, self.landlord)

    def test_full_happy_path(self):
        services.submit_listing(self.listing, actor=self.landlord)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.SUBMITTED)

        services.publish_listing(self.listing, actor=self.staff)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.PUBLISHED)
        self.assertIsNotNone(self.listing.published_at)

        self.assertEqual(AuditLog.objects.count(), 2)

    def test_reject_requires_reason(self):
        services.submit_listing(self.listing, actor=self.landlord)
        with self.assertRaises(services.ListingTransitionError):
            services.reject_listing(self.listing, actor=self.staff, reason="")

    def test_non_staff_cannot_publish(self):
        services.submit_listing(self.listing, actor=self.landlord)
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.publish_listing(self.listing, actor=self.landlord)

    def test_cannot_publish_draft(self):
        with self.assertRaises(services.ListingTransitionError):
            services.publish_listing(self.listing, actor=self.staff)
'''.strip() + "\n"

TEST_ENDPOINTS = '''
from rest_framework.test import APITestCase

from apps.properties import services

from .factories import make_listing, make_property, make_user


class ListingEndpointTests(APITestCase):
    def setUp(self):
        self.landlord = make_user("l@x.com")
        self.staff = make_user("s@x.com", is_staff=True)
        self.other = make_user("o@x.com")
        self.prop = make_property(self.landlord)

    def test_anonymous_cannot_create_listing(self):
        resp = self.client.post("/api/v1/listings/", {
            "property": str(self.prop.id), "transaction_type": "RENT",
            "price": "5000", "title": "Test",
        })
        self.assertEqual(resp.status_code, 401)

    def test_landlord_can_create_listing(self):
        self.client.force_authenticate(self.landlord)
        resp = self.client.post("/api/v1/listings/", {
            "property": str(self.prop.id), "transaction_type": "RENT",
            "price": "5000", "title": "Test",
        })
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_agent_without_authority_rejected(self):
        self.client.force_authenticate(self.other)
        resp = self.client.post("/api/v1/listings/", {
            "property": str(self.prop.id), "transaction_type": "RENT",
            "price": "5000", "title": "Test",
        })
        self.assertEqual(resp.status_code, 400)

    def test_draft_not_visible_to_anonymous(self):
        make_listing(self.prop, self.landlord, title="Draft")
        resp = self.client.get("/api/v1/listings/")
        self.assertEqual(resp.json()["count"], 0)

    def test_published_visible_to_anonymous(self):
        listing = make_listing(self.prop, self.landlord)
        services.submit_listing(listing, actor=self.landlord)
        services.publish_listing(listing, actor=self.staff)
        resp = self.client.get("/api/v1/listings/")
        self.assertEqual(resp.json()["count"], 1)
'''.strip() + "\n"

# ---------------------------------------------------------------------- manifest

FILES = {
    "apps/properties/__init__.py": PROPERTIES_INIT,
    "apps/properties/apps.py": PROPERTIES_APPS,
    "apps/properties/enums.py": PROPERTIES_ENUMS,
    "apps/properties/models.py": PROPERTIES_MODELS,
    "apps/properties/permissions.py": PROPERTIES_PERMISSIONS,
    "apps/properties/services.py": PROPERTIES_SERVICES,
    "apps/properties/serializers.py": PROPERTIES_SERIALIZERS,
    "apps/properties/views.py": PROPERTIES_VIEWS,
    "apps/properties/urls.py": PROPERTIES_URLS,
    "apps/properties/admin.py": PROPERTIES_ADMIN,
    "apps/properties/migrations/__init__.py": "",
    "apps/properties/tests/__init__.py": "",
    "apps/properties/tests/factories.py": TEST_FACTORIES,
    "apps/properties/tests/test_permissions.py": TEST_PERMISSIONS,
    "apps/properties/tests/test_listing_workflow.py": TEST_WORKFLOW,
    "apps/properties/tests/test_endpoints.py": TEST_ENDPOINTS,
    "apps/properties/management/__init__.py": "",
    "apps/properties/management/commands/__init__.py": "",
    "apps/properties/management/commands/seed_property_features.py": SEED_FEATURES,
}

# (path, old snippet, new snippet, description)
PATCHES = [
    (
        "config/settings/base.py",
        '    "apps.locations",\n',
        '    "apps.locations",\n    "apps.properties",\n',
        "settings: register apps.properties",
    ),
    (
        "config/urls.py",
        'path("api/v1/", include("apps.locations.urls")),\n',
        'path("api/v1/", include("apps.locations.urls")),\n'
        '    path("api/v1/", include("apps.properties.urls")),\n',
        "urls: mount apps.properties.urls",
    ),
    (
        "requirements.txt",
        "python-dotenv>=1.0\n",
        "python-dotenv>=1.0\ndrf-nested-routers>=0.94\n",
        "requirements: add drf-nested-routers",
    ),
]


# ---------------------------------------------------------------------- engine

def write_files(root: Path, force: bool) -> tuple[list[str], list[str]]:
    written, skipped = [], []
    for relative, content in FILES.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not force and target.read_text(encoding="utf-8") != content:
            skipped.append(relative)
            continue
        target.write_text(content, encoding="utf-8")
        written.append(relative)
    return written, skipped


def apply_patch(root: Path, relative: str, old: str, new: str, description: str) -> str:
    path = root / relative
    if not path.exists():
        return f"  SKIP   {description}  (file missing: {relative})"
    text = path.read_text(encoding="utf-8")
    if old not in text:
        marker = new.strip().split("\n")[0]
        if marker in text:
            return f"  ok     {description}  (already applied)"
        return f"  WARN   {description}  (snippet not found in {relative})"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"  PATCH  {description}"


def run_manage(root: Path, *args: str) -> int:
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings.dev"}
    return subprocess.run(
        [sys.executable, "manage.py", *args], cwd=root, env=env
    ).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold NyumbaLink Phase 2.")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    parser.add_argument("--check", action="store_true", help="run manage.py check afterwards")
    parser.add_argument("--dir", default=".", help="target directory (default: cwd)")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    if not (root / "manage.py").exists():
        print(f"No manage.py in {root}. Run from the project root.")
        return 1

    print(f"NyumbaLink Phase 2 -> {root}\n")

    written, skipped = write_files(root, args.force)
    print(f"Files: {len(written)} written, {len(skipped)} skipped")
    for path in skipped:
        print(f"  skipped (exists, use --force): {path}")

    print("\nPatching existing files:")
    patch_results = [apply_patch(root, *p) for p in PATCHES]
    print("\n".join(patch_results))

    if any(r.startswith("  WARN") for r in patch_results):
        print("\nSome patches did not match. Inspect those files by hand "
              "before continuing.")

    if args.check:
        print("\nRunning manage.py check ...")
        rc = run_manage(root, "check")
        if rc != 0:
            print("\ncheck failed — see error above. Most likely the new "
                  "drf-nested-routers dependency is not installed yet.")
            return rc

    print("""
Next steps (run in this order):

  1.  .\\venv\\Scripts\\python.exe -m pip install -r requirements.txt
      (installs drf-nested-routers, the only new dependency)

  2.  .\\venv\\Scripts\\python.exe manage.py check
      expected: System check identified no issues (0 silenced).

  3.  .\\venv\\Scripts\\python.exe manage.py makemigrations properties
      expected: Migrations for 'properties':
                  apps\\properties\\migrations\\0001_initial.py
                    + Create model AuditLog
                    + Create model PropertyFeature
                    + Create model Listing
                    + Create model Property
                    + Create model PropertyAuthority
                    + Create model ListingMedia
                    + Create model Report
                    + Create constraint ...

  4.  Read apps\\properties\\migrations\\0001_initial.py before applying.
      Look for THREE constraints in Meta.constraints:
        - property_both_coords_or_neither
        - report_exactly_one_target
        - uniq_authority_property_user
      If any is missing, stop.

  5.  .\\venv\\Scripts\\python.exe manage.py migrate
      expected: Applying properties.0001_initial... OK

  6.  .\\venv\\Scripts\\python.exe manage.py seed_property_features
      expected: Seeded 20 new features.

  7.  .\\venv\\Scripts\\python.exe manage.py test apps.properties
      expected: Ran 17 tests ... OK
      Then:    .\\venv\\Scripts\\python.exe manage.py test apps
      expected: Ran 24 tests ... OK

  8.  git add . && git commit -m "Phase 2: properties, listings, moderation, permissions"
      git tag phase-2
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())