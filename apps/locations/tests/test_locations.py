from django.test import TestCase
from django.urls import reverse

from apps.locations.models import District, Locality, Neighbourhood, Province


class LocationModelTests(TestCase):
    def setUp(self):
        self.province = Province.objects.create(name="Lusaka", slug="lusaka", code="LS")
        self.district = District.objects.create(
            province=self.province, name="Lusaka", slug="lusaka"
        )
        self.locality = Locality.objects.create(
            district=self.district, name="Lusaka", slug="lusaka"
        )

    def test_hierarchy(self):
        hood = Neighbourhood.objects.create(
            locality=self.locality, name="Kabulonga", slug="kabulonga"
        )
        self.assertEqual(hood.locality.district.province.name, "Lusaka")

    def test_province_list_endpoint(self):
        response = self.client.get("/api/v1/provinces/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
