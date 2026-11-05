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
