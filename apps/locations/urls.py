from rest_framework.routers import DefaultRouter

from .views import DistrictViewSet, LocalityViewSet, NeighbourhoodViewSet, ProvinceViewSet

router = DefaultRouter()
router.register("provinces", ProvinceViewSet, basename="province")
router.register("districts", DistrictViewSet, basename="district")
router.register("localities", LocalityViewSet, basename="locality")
router.register("neighbourhoods", NeighbourhoodViewSet, basename="neighbourhood")

urlpatterns = router.urls
