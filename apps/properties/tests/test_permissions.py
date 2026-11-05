from django.test import TestCase

from apps.properties.enums import ListingStatus
from apps.properties.models import PropertyAuthority
from apps.properties.permissions import (
    user_can_create_listing,
    user_can_edit_listing,
    user_can_manage_property,
)

from .factories import make_listing, make_property, make_user


class PermissionMatrixTests(TestCase):
    def setUp(self):
        self.landlord = make_user("landlord@x.com")
        self.agent = make_user("agent@x.com")
        self.other = make_user("other@x.com")
        self.staff = make_user("staff@x.com", is_staff=True)
        self.prop = make_property(self.landlord)

    def test_landlord_can_manage_own_property(self):
        self.assertTrue(user_can_manage_property(self.landlord, self.prop))

    def test_other_cannot_manage_property(self):
        self.assertFalse(user_can_manage_property(self.other, self.prop))

    def test_landlord_can_create_listing(self):
        self.assertTrue(user_can_create_listing(self.landlord, self.prop))

    def test_agent_without_authority_cannot_create_listing(self):
        self.assertFalse(user_can_create_listing(self.agent, self.prop))

    def test_agent_with_authority_can_create_listing(self):
        PropertyAuthority.objects.create(
            property=self.prop, granted_to=self.agent, granted_by=self.landlord
        )
        self.assertTrue(user_can_create_listing(self.agent, self.prop))

    def test_revoked_authority_blocks_agent(self):
        from django.utils import timezone
        PropertyAuthority.objects.create(
            property=self.prop, granted_to=self.agent, granted_by=self.landlord,
            revoked_at=timezone.now(),
        )
        self.assertFalse(user_can_create_listing(self.agent, self.prop))

    def test_landlord_can_edit_agent_listing(self):
        PropertyAuthority.objects.create(
            property=self.prop, granted_to=self.agent, granted_by=self.landlord
        )
        listing = make_listing(self.prop, self.agent)
        self.assertTrue(user_can_edit_listing(self.landlord, listing))

    def test_staff_bypasses(self):
        listing = make_listing(self.prop, self.landlord)
        self.assertTrue(user_can_edit_listing(self.staff, listing))
        self.assertTrue(user_can_create_listing(self.staff, self.prop))
