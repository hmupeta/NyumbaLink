from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Conversation, Message, ViewingRequest, MessageReaction
from .serializers import ConversationSerializer, MessageSerializer, ViewingRequestSerializer
from apps.properties.models import Listing

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(Q(seeker=self.request.user) | Q(landlord=self.request.user)).order_by("-updated_at")

    @action(detail=False, methods=["post"])
    def start(self, request):
        listing_id = request.data.get("listing_id")
        try:
            listing = Listing.objects.get(id=listing_id)
            if listing.created_by == request.user:
                return Response({"detail": "You cannot message yourself."}, status=400)
            
            conv, created = Conversation.objects.get_or_create(
                listing=listing, seeker=request.user, landlord=listing.created_by
            )
            return Response(ConversationSerializer(conv).data)
        except Listing.DoesNotExist:
            return Response({"detail": "Listing not found."}, status=404)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        conv_id = self.kwargs.get("conversation_pk")
        qs = Message.objects.filter(conversation_id=conv_id).filter(
            Q(conversation__seeker=self.request.user) | Q(conversation__landlord=self.request.user)
        ).select_related("reply_to", "sender").prefetch_related("reactions")

        # Mark messages as read if I am NOT the sender
        Message.objects.filter(conversation_id=conv_id, is_read=False).exclude(sender=self.request.user).update(is_read=True)
        return qs

    def perform_create(self, serializer):
        conv_id = self.kwargs.get("conversation_pk")
        conv = Conversation.objects.get(id=conv_id)
        if self.request.user not in (conv.seeker, conv.landlord):
            raise permissions.PermissionDenied("Not your conversation")
        serializer.save(conversation=conv, sender=self.request.user)
        conv.save() # update updated_at

    @action(detail=True, methods=["post"])
    def react(self, request, conversation_pk=None, pk=None):
        message = self.get_object()
        emoji = request.data.get("emoji")
        
        # Toggle reaction
        reaction, created = MessageReaction.objects.get_or_create(
            message=message, user=request.user, defaults={"emoji": emoji}
        )
        if not created:
            if reaction.emoji == emoji:
                reaction.delete()
                return Response({"status": "removed"})
            else:
                reaction.emoji = emoji
                reaction.save()
        return Response({"status": "added", "emoji": emoji})


class ViewingRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ViewingRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ViewingRequest.objects.filter(
            Q(seeker=self.request.user) | Q(listing__created_by=self.request.user)
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(seeker=self.request.user)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        viewing = self.get_object()
        if viewing.listing.created_by != request.user:
            return Response({"detail": "Only the landlord can update this."}, status=403)
        
        new_status = request.data.get("status")
        if new_status not in ["APPROVED", "REJECTED"]:
            return Response({"detail": "Invalid status."}, status=400)
        
        viewing.status = new_status
        viewing.save()
        return Response(ViewingRequestSerializer(viewing).data)
