
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WalletViewSet, UnlockViewSet

router = DefaultRouter()
router.register("wallet", WalletViewSet, basename="wallet")
router.register("unlock", UnlockViewSet, basename="unlock")

urlpatterns = router.urls
