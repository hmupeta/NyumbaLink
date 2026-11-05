from django.db.models import Q
from django.utils import timezone

from .models import Listing, Property, PropertyAuthority


def user_is_moderator(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def user_can_manage_property(user, prop: Property) -> bool:
    if user_is_moderator(user):
        return True
    return prop.submitted_by_id == user.id


def user_can_create_listing(user, prop: Property) -> bool:
    """A listing may be created by the property submitter, a moderator,
    or a user holding a live PropertyAuthority with can_list=True."""
    if user_is_moderator(user):
        return True
    if prop.submitted_by_id == user.id:
        return True
    return PropertyAuthority.objects.filter(
        property=prop,
        granted_to=user,
        can_list=True,
        revoked_at__isnull=True,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    ).exists()


def user_can_edit_listing(user, listing: Listing) -> bool:
    """The advertiser may edit their own listing. The property submitter may
    also edit it — this is how an owner withdraws an agent's advertisement."""
    if user_is_moderator(user):
        return True
    if listing.created_by_id == user.id:
        return True
    return listing.property.submitted_by_id == user.id


def user_can_view_listing(user, listing: Listing) -> bool:
    from .enums import ListingStatus

    if listing.status == ListingStatus.PUBLISHED:
        return True
    if not user or not user.is_authenticated:
        return False
    return user_can_edit_listing(user, listing)
