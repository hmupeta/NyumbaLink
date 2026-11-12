from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .enums import ListingStatus
from django.db.models import Sum, Count
from .models import HeroImage, Listing, ListingMedia, Property, Report, SavedListing
from apps.payments.models import ContactUnlock
from apps.messaging.models import Conversation
from .permissions import user_can_edit_listing, user_can_manage_property, user_is_moderator
from .serializers import (
    PropertyAuthoritySerializer,
    ListingActionSerializer,
    ListingMediaSerializer,
    ListingSerializer,
    PropertySerializer,
    ReportSerializer,
    HeroImageSerializer,
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
        return qs.exclude(property__status='OCCUPIED')

    def perform_create(self, serializer):
        serializer.save(submitted_by=self.request.user)


class ListingFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
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
        return qs.exclude(property__status='OCCUPIED').filter(property__features__slug__in=slugs).distinct()


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
        
        # Staff see everything (for moderation)
        if user.is_authenticated and user.is_staff:
            return qs.exclude(property__status='OCCUPIED')
            
        # The my_listings action handles its own filtering
        if self.action == "my_listings":
            return qs.exclude(property__status='OCCUPIED')

        # PUBLIC LIST VIEW (Homepage): ALWAYS only return PUBLISHED
        if self.action == "list":
            return qs.filter(status=ListingStatus.PUBLISHED)

        # DETAIL ACTIONS (Update, Delete, Submit, Publish):
        # Allow if it's published OR if the user owns it
        if user.is_authenticated:
            return qs.exclude(property__status='OCCUPIED').filter(
                Q(status=ListingStatus.PUBLISHED)
                | Q(created_by=user)
                | Q(property__submitted_by=user)
            )

        # Anonymous users can only see published listings
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
    def track_view(self, request, pk=None):
        listing = self.get_object()
        # Basic logic: don't track if the owner views it
        if request.user.is_authenticated and listing.created_by == request.user:
            return Response({"status": "ignored"})
        
        listing.views_count += 1
        listing.save(update_fields=["views_count"])
        return Response({"status": "tracked"})

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=403)
        
        # Aggregate data for this landlord
        listings = Listing.objects.filter(created_by=request.user)
        
        total_views = listings.aggregate(total=Sum("views_count"))["total"] or 0
        total_saves = SavedListing.objects.filter(listing__in=listings).count()
        total_unlocks = ContactUnlock.objects.filter(listing__in=listings).count()
        total_conversations = Conversation.objects.filter(listing__in=listings).count()
        
        # Get per-listing stats for the chart
        chart_data = []
        for l in listings:
            chart_data.append({
                "id": str(l.id),
                "title": l.title,
                "views": l.views_count,
                "saves": l.saved_by.count(),
                "unlocks": l.unlocks.count() if hasattr(l, 'unlocks') else 0,
            })

        return Response({
            "totals": {
                "views": total_views,
                "saves": total_saves,
                "unlocks": total_unlocks,
                "conversations": total_conversations
            },
            "chart_data": chart_data
        })

    @action(detail=False, methods=["get"])
    def my_listings(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=401)
            
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Fetching listings for user: {request.user.email} (ID: {request.user.id})")

        qs = Listing.objects.filter(
            Q(created_by=request.user) | Q(property__submitted_by=request.user)
        ).select_related(
            "property__neighbourhood__locality__district__province",
            "created_by",
        ).prefetch_related("media").order_by("-created_at")
        
        logger.info(f"Found {qs.count()} listings for {request.user.email}")

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def recommendations(self, request):
        if not request.user.is_authenticated:
            return Response([])
        
        # Simple logic: return 3 random published listings not owned by the user
        recs = Listing.objects.filter(status=ListingStatus.PUBLISHED).exclude(
            created_by=request.user
        ).order_by("?")[:3]
        
        serializer = self.get_serializer(recs, many=True)
        return Response(serializer.data)

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
        import cloudinary.uploader
        from django.conf import settings
        import os

        listing = Listing.objects.get(pk=self.kwargs["listing_pk"])
        if not user_can_edit_listing(self.request.user, listing):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot add media to this listing")
        
        file = self.request.FILES.get('file')
        if not file:
            return serializer.save(listing=listing)

        # Force direct upload to Cloudinary using the env vars
        try:
            cloudinary.config(
                cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
                api_key=os.environ.get("CLOUDINARY_API_KEY"),
                api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
                secure=True
            )
            result = cloudinary.uploader.upload(file, folder="nyumbalink/")
            
            # Save the ListingMedia record with the Cloudinary URL as the file name
            media = serializer.save(listing=listing)
            media.file.name = result['secure_url']
            media.save()
        except Exception as e:
            print("CLOUDINARY UPLOAD FAILED:", str(e))
            # Fallback to local storage if Cloudinary fails
            serializer.save(listing=listing)

    def perform_destroy(self, instance):
        if not user_can_edit_listing(self.request.user, instance.listing):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot remove media from this listing")
        instance.delete()


class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = Report.objects.select_related("reporter", "target_listing", "target_user")
        if user_is_moderator(self.request.user):
            return qs.exclude(property__status='OCCUPIED')
        return qs.exclude(property__status='OCCUPIED').filter(reporter=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        if not user_is_moderator(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only moderators can update reports")
        return super().partial_update(request, *args, **kwargs)


class SavedListingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SavedListing.objects.filter(user=self.request.user).select_related("listing")
    
    def create(self, request):
        listing_id = request.data.get("listing_id")
        saved, created = SavedListing.objects.get_or_create(user=request.user, listing_id=listing_id)
        return Response({"status": "saved"})
        
    def destroy(self, request, pk=None):
        # pk here will be the listing_id based on our frontend URL structure
        SavedListing.objects.filter(user=request.user, listing_id=pk).delete()
        return Response(status=204)


class HeroImageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HeroImage.objects.filter(is_active=True)
    serializer_class = HeroImageSerializer
    permission_classes = [permissions.AllowAny]


class PropertyAuthorityViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyAuthoritySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        # Landlords see who they granted access to; Agents see what they have access to
        from django.db.models import Q
        return PropertyAuthority.objects.filter(
            Q(granted_by=self.request.user) | Q(granted_to=self.request.user)
        ).select_related("property", "granted_to")

    def perform_create(self, serializer):
        property_id = self.request.data.get("property")
        email = self.request.data.get("granted_to_email")
        
        from django.contrib.auth import get_user_model
        from .models import Property
        from apps.notifications.services import create_notification
        
        User = get_user_model()
        prop = Property.objects.get(id=property_id)
        
        if prop.submitted_by != self.request.user:
            raise permissions.PermissionDenied("Only the property owner can grant authority.")
            
        agent = User.objects.filter(email__iexact=email).first()
        if not agent:
            raise serializers.ValidationError("No user found with that email.")
            
        authority = serializer.save(property=prop, granted_to=agent, granted_by=self.request.user)
        
        create_notification(
            user=agent,
            title="New Property Access",
            message=f"You have been granted access to manage {prop.neighbourhood.name}.",
            link=f"/dashboard"
        )
