from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from .enums import ListingStatus
from .models import AuditLog, Listing
from .permissions import user_can_edit_listing, user_is_moderator


class ListingTransitionError(Exception):
    pass


def _audit(actor, action, listing, **payload):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type="Listing",
        target_id=listing.id,
        payload=payload,
    )


def _transition(listing, from_states, to_state, *, actor, note=""):
    if listing.status not in from_states:
        raise ListingTransitionError(
            f"Cannot move listing from {listing.status} to {to_state}"
        )
    listing.status = to_state
    if note:
        listing.moderation_note = note
    return listing


@transaction.atomic
def submit_listing(listing: Listing, *, actor) -> Listing:
    if not user_can_edit_listing(actor, listing):
        raise PermissionDenied("You cannot submit this listing")
    _transition(listing, {ListingStatus.DRAFT}, ListingStatus.SUBMITTED, actor=actor)
    listing.save(update_fields=["status", "moderation_note", "updated_at"])
    _audit(actor, "listing.submitted", listing)
    return listing


@transaction.atomic
def publish_listing(listing: Listing, *, actor, note="") -> Listing:
    if not user_is_moderator(actor):
        raise PermissionDenied("Only moderators can publish listings")
    _transition(listing, {ListingStatus.SUBMITTED}, ListingStatus.PUBLISHED, actor=actor, note=note)
    listing.published_at = timezone.now()
    listing.save(update_fields=["status", "published_at", "moderation_note", "updated_at"])
    _audit(actor, "listing.published", listing, note=note)
    return listing


@transaction.atomic
def reject_listing(listing: Listing, *, actor, reason: str) -> Listing:
    if not user_is_moderator(actor):
        raise PermissionDenied("Only moderators can reject listings")
    if not reason:
        raise ListingTransitionError("A rejection reason is required")
    _transition(listing, {ListingStatus.SUBMITTED}, ListingStatus.REJECTED, actor=actor, note=reason)
    listing.rejection_reason = reason
    listing.save(update_fields=["status", "rejection_reason", "moderation_note", "updated_at"])
    _audit(actor, "listing.rejected", listing, reason=reason)
    return listing


@transaction.atomic
def withdraw_listing(listing: Listing, *, actor) -> Listing:
    if not user_can_edit_listing(actor, listing):
        raise PermissionDenied("You cannot withdraw this listing")
    _transition(
        listing,
        {ListingStatus.PUBLISHED, ListingStatus.REJECTED},
        ListingStatus.WITHDRAWN,
        actor=actor,
    )
    listing.save(update_fields=["status", "updated_at"])
    _audit(actor, "listing.withdrawn", listing)
    return listing


@transaction.atomic
def archive_listing(listing: Listing, *, actor) -> Listing:
    if not user_can_edit_listing(actor, listing):
        raise PermissionDenied("You cannot archive this listing")
    _transition(
        listing,
        {ListingStatus.PUBLISHED, ListingStatus.REJECTED, ListingStatus.WITHDRAWN, ListingStatus.EXPIRED},
        ListingStatus.ARCHIVED,
        actor=actor,
    )
    listing.save(update_fields=["status", "updated_at"])
    _audit(actor, "listing.archived", listing)
    return listing
