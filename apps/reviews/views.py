from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import Review
from .serializers import ReviewSerializer, PublicProfileSerializer

User = get_user_model()

class PublicProfileViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    lookup_field = "pk"

    def retrieve(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        serializer = PublicProfileSerializer(user, context={"request": request})
        return Response(serializer.data)

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["post", "get", "head", "options"]

    def get_queryset(self):
        return Review.objects.filter(landlord_id=self.kwargs.get("profile_pk"))

    def perform_create(self, serializer):
        landlord_id = self.kwargs.get("profile_pk")
        if str(self.request.user.id) == str(landlord_id):
            raise permissions.PermissionDenied("You cannot review yourself.")
        
        # Check if already reviewed
        if Review.objects.filter(landlord_id=landlord_id, reviewer=self.request.user).exists():
            raise permissions.PermissionDenied("You have already reviewed this landlord.")

        serializer.save(landlord_id=landlord_id, reviewer=self.request.user)
