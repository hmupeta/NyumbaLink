from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.messaging.models import Message, ViewingRequest
from apps.reviews.models import Review
from .services import create_notification

@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    if created:
        conv = instance.conversation
        # Notify the receiver
        receiver = conv.landlord if instance.sender == conv.seeker else conv.seeker
        create_notification(
            user=receiver,
            title=f"New message from {instance.sender.first_name or instance.sender.email}",
            message=instance.body[:50] + ("..." if len(instance.body) > 50 else ""),
            link=f"/inbox?c={conv.id}"
        )

@receiver(post_save, sender=ViewingRequest)
def notify_viewing_request(sender, instance, created, **kwargs):
    if created:
        create_notification(
            user=instance.listing.created_by,
            title="New Viewing Request",
            message=f"{instance.seeker.email} requested to view {instance.listing.title}",
            link=f"/dashboard?tab=viewings"
        )
    else:
        # If status was updated (e.g., APPROVED/REJECTED)
        if instance.status != "PENDING":
            create_notification(
                user=instance.seeker,
                title=f"Viewing Request {instance.status}",
                message=f"Your request to view {instance.listing.title} was {instance.status.lower()}.",
                link=f"/listings/{instance.listing.id}"
            )

@receiver(post_save, sender=Review)
def notify_new_review(sender, instance, created, **kwargs):
    if created:
        create_notification(
            user=instance.landlord,
            title="New Review Received",
            message=f"You received a {instance.rating}-star review.",
            link=f"/profiles/{instance.landlord.id}"
        )
