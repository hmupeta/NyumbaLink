from django.test import TestCase

from apps.properties import services
from apps.properties.enums import ListingStatus
from apps.properties.models import AuditLog

from .factories import make_listing, make_property, make_user


class ListingWorkflowTests(TestCase):
    def setUp(self):
        self.landlord = make_user("l@x.com")
        self.staff = make_user("s@x.com", is_staff=True)
        self.prop = make_property(self.landlord)
        self.listing = make_listing(self.prop, self.landlord)

    def test_full_happy_path(self):
        services.submit_listing(self.listing, actor=self.landlord)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.SUBMITTED)

        services.publish_listing(self.listing, actor=self.staff)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, ListingStatus.PUBLISHED)
        self.assertIsNotNone(self.listing.published_at)

        self.assertEqual(AuditLog.objects.count(), 2)

    def test_reject_requires_reason(self):
        services.submit_listing(self.listing, actor=self.landlord)
        with self.assertRaises(services.ListingTransitionError):
            services.reject_listing(self.listing, actor=self.staff, reason="")

    def test_non_staff_cannot_publish(self):
        services.submit_listing(self.listing, actor=self.landlord)
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.publish_listing(self.listing, actor=self.landlord)

    def test_cannot_publish_draft(self):
        with self.assertRaises(services.ListingTransitionError):
            services.publish_listing(self.listing, actor=self.staff)
