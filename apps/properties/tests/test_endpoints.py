from rest_framework.test import APITestCase

from apps.properties import services

from .factories import make_listing, make_property, make_user


class ListingEndpointTests(APITestCase):
    def setUp(self):
        self.landlord = make_user("l@x.com")
        self.staff = make_user("s@x.com", is_staff=True)
        self.other = make_user("o@x.com")
        self.prop = make_property(self.landlord)

    def test_anonymous_cannot_create_listing(self):
        resp = self.client.post("/api/v1/listings/", {
            "property": str(self.prop.id), "transaction_type": "RENT",
            "price": "5000", "title": "Test",
        })
        # 403 not 401: SessionAuthentication declares no authenticate_header().
        # This becomes 401 when token auth arrives in Phase 3.
        self.assertEqual(resp.status_code, 403)

    def test_landlord_can_create_listing(self):
        self.client.force_authenticate(self.landlord)
        resp = self.client.post("/api/v1/listings/", {
            "property": str(self.prop.id), "transaction_type": "RENT",
            "price": "5000", "title": "Test",
        })
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_agent_without_authority_rejected(self):
        self.client.force_authenticate(self.other)
        resp = self.client.post("/api/v1/listings/", {
            "property": str(self.prop.id), "transaction_type": "RENT",
            "price": "5000", "title": "Test",
        })
        self.assertEqual(resp.status_code, 400)

    def test_draft_not_visible_to_anonymous(self):
        make_listing(self.prop, self.landlord, title="Draft")
        resp = self.client.get("/api/v1/listings/")
        self.assertEqual(resp.json()["count"], 0)

    def test_published_visible_to_anonymous(self):
        listing = make_listing(self.prop, self.landlord)
        services.submit_listing(listing, actor=self.landlord)
        services.publish_listing(listing, actor=self.staff)
        resp = self.client.get("/api/v1/listings/")
        self.assertEqual(resp.json()["count"], 1)
