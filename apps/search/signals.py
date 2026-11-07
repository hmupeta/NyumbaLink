from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from apps.properties.models import Listing
from .models import SavedSearch

@receiver(post_save, sender=Listing)
def notify_saved_searches(sender, instance, created, **kwargs):
    # We only care when a listing becomes PUBLISHED
    if instance.status != "PUBLISHED":
        return

    # Find matching saved searches
    matches = SavedSearch.objects.filter(
        Q(transaction_type="") | Q(transaction_type=instance.transaction_type),
        Q(property_type="") | Q(property_type=instance.property.property_type),
    )

    # Filter by price
    matches = matches.filter(
        Q(min_price__isnull=True) | Q(min_price__lte=instance.price),
        Q(max_price__isnull=True) | Q(max_price__gte=instance.price),
    )

    # Filter by location
    for search in matches:
        if search.province and search.province.lower() != instance.property.neighbourhood.locality.district.province.name.lower():
            continue
        if search.district and search.district.lower() != instance.property.neighbourhood.locality.district.name.lower():
            continue
        if search.min_bedrooms and instance.property.bedrooms and instance.property.bedrooms < search.min_bedrooms:
            continue
            
        # Send Email (using console backend in development)
        subject = f"New listing matches your saved search: {search.name}"
        message = f"""
Hello {search.user.first_name or search.user.email},

A new property matching your saved search "{search.name}" has just been listed on NyumbaLink!

Title: {instance.title}
Price: {instance.currency} {instance.price}
Location: {instance.property.neighbourhood.name}

View it here: http://localhost:5173/listings/{instance.id}

Best regards,
The NyumbaLink Team
        """
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [search.user.email],
            fail_silently=True,
        )
