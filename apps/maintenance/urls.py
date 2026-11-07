from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MaintenanceRequestViewSet

router = DefaultRouter()
router.register("maintenance", MaintenanceRequestViewSet, basename="maintenance")
urlpatterns = router.urls
