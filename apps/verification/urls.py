from django.urls import path, include
from rest_framework_nested import routers
from .views import VerificationCaseViewSet, VerificationDocumentViewSet

router = routers.DefaultRouter()
router.register("verifications", VerificationCaseViewSet, basename="verification")

nested_router = routers.NestedDefaultRouter(router, "verifications", lookup="case")
nested_router.register("documents", VerificationDocumentViewSet, basename="verification-documents")

urlpatterns = router.urls + nested_router.urls
