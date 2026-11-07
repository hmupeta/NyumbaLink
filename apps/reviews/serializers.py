from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Review
from apps.properties.models import Listing
from apps.properties.serializers import ListingSerializer

User = get_user_model()

class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.first_name", read_only=True)
    reviewer_email = serializers.CharField(source="reviewer.email", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "landlord", "reviewer", "reviewer_name", "reviewer_email", "rating", "comment", "created_at")
        read_only_fields = ("id", "landlord", "reviewer", "created_at")

class PublicProfileSerializer(serializers.ModelSerializer):
    listings = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    verification_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email", "avatar", "cover_photo", "bio", "listings", "reviews", "average_rating", "verification_status")

    def get_listings(self, obj):
        # Only show published listings for this landlord
        listings = Listing.objects.filter(created_by=obj, status="PUBLISHED")
        # We pass context so the ListingSerializer can process is_saved correctly
        return ListingSerializer(listings, many=True, context=self.context).data

    def get_reviews(self, obj):
        reviews = obj.reviews_received.all().order_by("-created_at")
        return ReviewSerializer(reviews, many=True).data

    def get_average_rating(self, obj):
        reviews = obj.reviews_received.all()
        if not reviews: return None
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    def get_verification_status(self, obj):
        # Check if they have an approved IDENTITY verification
        has_id = obj.verification_cases.filter(verification_type="IDENTITY", status="APPROVED").exists()
        return {"identity": has_id}
