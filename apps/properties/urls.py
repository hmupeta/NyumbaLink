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
