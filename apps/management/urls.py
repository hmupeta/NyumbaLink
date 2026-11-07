from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import LeaseViewSet, RentRecordViewSet

router = DefaultRouter()
router.register("leases", LeaseViewSet, basename="lease")

lease_router = routers.NestedDefaultRouter(router, "leases", lookup="lease")
lease_router.register("rent-records", RentRecordViewSet, basename="rent-record")

urlpatterns = router.urls + lease_router.urls
