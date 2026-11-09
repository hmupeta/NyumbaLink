from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action

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


from rest_framework import permissions, status
from rest_framework.response import Response
from django.utils.text import slugify

class NeighbourhoodViewSet(viewsets.ModelViewSet):
    queryset = Neighbourhood.objects.select_related("locality").order_by("name")
    serializer_class = NeighbourhoodSerializer
    filterset_fields = ("locality",)
    search_fields = ("name",)
    lookup_field = "slug"
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def create(self, request):
        name = request.data.get("name")
        if not name:
            return Response({"detail": "Name is required"}, status=400)
            
        # Check if it already exists (case-insensitive)
        existing = Neighbourhood.objects.filter(name__iexact=name).first()
        if existing:
            return Response(NeighbourhoodSerializer(existing).data, status=200)

        # If it's brand new, attach it to a default locality (e.g. Lusaka)
        from apps.locations.models import Locality
        default_locality = Locality.objects.first()
        if not default_locality:
            return Response({"detail": "No localities configured in the system."}, status=500)

        slug = slugify(name)
        # Ensure slug is unique
        original_slug = slug
        counter = 1
        while Neighbourhood.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1

        new_hood = Neighbourhood.objects.create(
            locality=default_locality,
            name=name,
            slug=slug
        )
        return Response(NeighbourhoodSerializer(new_hood).data, status=201)

    @action(detail=False, methods=["get"])
    def top(self, request):
        # Find neighbourhoods with published listings, ordered by most listings
        top_hoods = Neighbourhood.objects.annotate(
            listing_count=Count(
                'properties__listings',
                filter=Q(properties__listings__status='PUBLISHED')
            )
        ).filter(listing_count__gt=0).order_by('-listing_count')[:5]
        
        data = []
        for hood in top_hoods:
            data.append({
                "id": str(hood.id),
                "name": hood.name,
                "slug": hood.slug,
                "locality_name": hood.locality.name,
                "listing_count": hood.listing_count
            })
        return Response(data)

