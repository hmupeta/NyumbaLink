from rest_framework import serializers

from .enums import ListingStatus
from .models import HeroImage, Listing, ListingMedia, Property, PropertyFeature
from .permissions import user_can_create_listing


class PropertyFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyFeature
        fields = ("id", "name", "slug", "category")


class ListingMediaSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = ListingMedia
        fields = ("id", "listing", "file", "media_type", "caption", "display_order")
        read_only_fields = ("id", "listing")

    def get_file(self, obj):
        if not obj.file:
            return None
        
        name = str(obj.file.name)
        
        # 1. External or Cloudinary URL (already absolute)
        if name.startswith('http://') or name.startswith('https://'):
            return name
            
        # 2. Local file: build the absolute URL (e.g., http://localhost:8000/media/...)
        try:
            url = obj.file.url
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(url)
            return url
        except Exception:
            return None



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
    is_saved = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = (
            "id", "property", "property_summary", "created_by", "created_by_email",
            "transaction_type", "price", "currency", "price_period",
            "deposit_months", "title", "description", "available_from",
            "status", "published_at", "expires_at", "rejection_reason",
            "moderation_note", "media", "is_saved", "views_count", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "created_by", "status", "published_at", "expires_at",
            "rejection_reason", "moderation_note", "created_at", "updated_at",
        )

    def get_is_saved(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.saved_by.filter(user=request.user).exists()
        return False

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


class HeroImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroImage
        fields = ("id", "title", "subtitle", "image", "display_order")
