from django.conf import settings
from django.db import models
from apps.core.models import TimeStampedModel

class Conversation(TimeStampedModel):
    listing = models.ForeignKey("properties.Listing", on_delete=models.CASCADE, related_name="conversations")
    seeker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seeker_conversations")
    landlord = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="landlord_conversations")
    
    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["listing", "seeker", "landlord"], name="uniq_listing_seeker_landlord"),
        ]

    def __str__(self):
        return f"{self.seeker.email} ↔ {self.landlord.email} ({self.listing.title})"

class Message(TimeStampedModel):
    class MessageType(models.TextChoices):
        TEXT = "TEXT", "Text"
        IMAGE = "IMAGE", "Image"
        AUDIO = "AUDIO", "Audio"
        FILE = "FILE", "File"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField(blank=True)
    
    # Media fields
    message_type = models.CharField(max_length=16, choices=MessageType.choices, default=MessageType.TEXT)
    file = models.FileField(upload_to="chat_files/", null=True, blank=True)

    # WhatsApp Features
    is_read = models.BooleanField(default=False)
    reply_to = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")

    class Meta(TimeStampedModel.Meta):
        ordering = ["created_at"]

    def __str__(self):
        return f"From {self.sender.email}: {self.message_type}"

class MessageReaction(TimeStampedModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["message", "user"], name="uniq_message_user_reaction"),
        ]

class ViewingRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    listing = models.ForeignKey("properties.Listing", on_delete=models.CASCADE, related_name="viewing_requests")
    seeker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="viewing_requests")
    requested_date = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"Viewing for {self.listing.title} by {self.seeker.email} ({self.status})"
