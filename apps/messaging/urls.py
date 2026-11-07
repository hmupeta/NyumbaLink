from django.urls import path, include
from rest_framework_nested import routers
from .views import ConversationViewSet, MessageViewSet, ViewingRequestViewSet

router = routers.DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("viewings", ViewingRequestViewSet, basename="viewing")

nested_router = routers.NestedDefaultRouter(router, "conversations", lookup="conversation")
nested_router.register("messages", MessageViewSet, basename="conversation-messages")

urlpatterns = router.urls + nested_router.urls
