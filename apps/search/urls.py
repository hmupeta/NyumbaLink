from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SavedSearchViewSet

router = DefaultRouter()
router.register("saved-searches", SavedSearchViewSet, basename="saved-search")
urlpatterns = router.urls
