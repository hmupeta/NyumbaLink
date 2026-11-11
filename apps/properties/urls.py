from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers

from .views import HeroImageViewSet, ListingMediaViewSet, ListingViewSet, PropertyViewSet, ReportViewSet, SavedListingViewSet

router = DefaultRouter()
router.register("properties", PropertyViewSet, basename="property")
router.register("listings", ListingViewSet, basename="listing")
router.register("reports", ReportViewSet, basename="report")
router.register("saved-listings", SavedListingViewSet, basename="saved-listing")
router.register("hero-images", HeroImageViewSet, basename="hero-image")
router.register("authorities", PropertyAuthorityViewSet, basename="authority")

listing_router = nested_routers.NestedDefaultRouter(router, "listings", lookup="listing")
listing_router.register("media", ListingMediaViewSet, basename="listing-media")

urlpatterns = router.urls + listing_router.urls
