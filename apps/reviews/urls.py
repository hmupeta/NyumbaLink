from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import PublicProfileViewSet, ReviewViewSet

router = DefaultRouter()
router.register("profiles", PublicProfileViewSet, basename="profile")

# Nested router for reviews under profiles
profile_router = routers.NestedDefaultRouter(router, "profiles", lookup="profile")
profile_router.register("reviews", ReviewViewSet, basename="profile-reviews")

urlpatterns = router.urls + profile_router.urls
