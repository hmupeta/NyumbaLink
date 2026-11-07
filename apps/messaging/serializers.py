from rest_framework import serializers
from .models import Conversation, Message, ViewingRequest, MessageReaction

class MessageReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReaction
        fields = ("id", "user", "emoji")

class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source="sender.email", read_only=True)
    reply_to_text = serializers.SerializerMethodField()
    reply_to_sender = serializers.SerializerMethodField()
    reactions = MessageReactionSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ("id", "sender", "sender_email", "body", "message_type", "file", "file_url", "created_at", "is_read", "reply_to", "reply_to_text", "reply_to_sender", "reactions")
        read_only_fields = ("id", "sender", "created_at", "is_read")
        extra_kwargs = {"file": {"write_only": True}}

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

    def get_reply_to_text(self, obj):
        if obj.reply_to:
            return obj.reply_to.body or f"[{obj.reply_to.message_type}]"
        return None

    def get_reply_to_sender(self, obj):
        if obj.reply_to:
            return obj.reply_to.sender.email
        return None

class ConversationSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    seeker_email = serializers.CharField(source="seeker.email", read_only=True)
    landlord_email = serializers.CharField(source="landlord.email", read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ("id", "listing", "listing_title", "seeker", "seeker_email", "landlord", "landlord_email", "last_message", "updated_at")

    def get_last_message(self, obj):
        msg = obj.messages.last()
        if not msg: return None
        return {"body": msg.body or f"[{msg.message_type}]", "created_at": msg.created_at}

class ViewingRequestSerializer(serializers.ModelSerializer):
    seeker_email = serializers.CharField(source="seeker.email", read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = ViewingRequest
        fields = ("id", "listing", "listing_title", "seeker", "seeker_email", "requested_date", "status", "note", "created_at")
        read_only_fields = ("id", "seeker", "status", "created_at")
