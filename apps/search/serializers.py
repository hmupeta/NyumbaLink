from rest_framework import serializers
from .models import SavedSearch

class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ("id", "name", "query", "transaction_type", "property_type", "province", "district", "min_price", "max_price", "min_bedrooms", "created_at")
        read_only_fields = ("id", "created_at")
