from rest_framework import viewsets

from .models import District, Locality, Neighbourhood, Province
from .serializers import (
    DistrictSerializer,
    LocalitySerializer,
    NeighbourhoodSerializer,
    ProvinceSerializer,
)


class ProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Province.objects.all().order_by("name")
    serializer_class = ProvinceSerializer
    search_fields = ("name", "code")
    lookup_field = "slug"


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = District.objects.select_related("province").order_by("name")
    serializer_class = DistrictSerializer
    filterset_fields = ("province",)
    search_fields = ("name",)
    lookup_field = "slug"


class LocalityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Locality.objects.select_related("district").order_by("name")
    serializer_class = LocalitySerializer
    filterset_fields = ("district",)
    search_fields = ("name",)
    lookup_field = "slug"


class NeighbourhoodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Neighbourhood.objects.select_related("locality").order_by("name")
    serializer_class = NeighbourhoodSerializer
    filterset_fields = ("locality",)
    search_fields = ("name",)
    lookup_field = "slug"
