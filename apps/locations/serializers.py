from rest_framework import serializers

from .models import District, Locality, Neighbourhood, Province


class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ("id", "name", "slug", "code")


class DistrictSerializer(serializers.ModelSerializer):
    province_name = serializers.CharField(source="province.name", read_only=True)

    class Meta:
        model = District
        fields = ("id", "name", "slug", "province", "province_name")


class LocalitySerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = Locality
        fields = ("id", "name", "slug", "district", "district_name")


class NeighbourhoodSerializer(serializers.ModelSerializer):
    locality_name = serializers.CharField(source="locality.name", read_only=True)

    class Meta:
        model = Neighbourhood
        fields = ("id", "name", "slug", "locality", "locality_name", "aliases")
