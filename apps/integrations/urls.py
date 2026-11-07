from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentSettingsViewSet

router = DefaultRouter()
router.register("payment-settings", PaymentSettingsViewSet, basename="payment-settings")

urlpatterns = router.urls
