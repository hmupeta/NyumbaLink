
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UnlockViewSet, RentPaymentViewSet

router = DefaultRouter()
router.register("unlock", UnlockViewSet, basename="unlock")
router.register("rent", RentPaymentViewSet, basename="rent")

urlpatterns = router.urls
