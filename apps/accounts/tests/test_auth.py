from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class AuthEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="a@x.com", password="testpass123", first_name="A"
        )

    def test_register_creates_user_and_sets_cookies(self):
        resp = self.client.post("/api/v1/auth/register/", {
            "email": "New@Example.com",
            "password": "supersecret123",
            "first_name": "New",
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["user"]["email"], "new@example.com")
        self.assertIn("access", resp.cookies)
        self.assertIn("refresh", resp.cookies)
        self.assertTrue(resp.cookies["access"]["httponly"])

    def test_register_rejects_duplicate_email(self):
        resp = self.client.post("/api/v1/auth/register/", {
            "email": "A@X.com", "password": "supersecret123",
        })
        self.assertEqual(resp.status_code, 400)

    def test_register_rejects_short_password(self):
        resp = self.client.post("/api/v1/auth/register/", {
            "email": "b@x.com", "password": "short",
        })
        self.assertEqual(resp.status_code, 400)

    def test_login_sets_cookies(self):
        resp = self.client.post("/api/v1/auth/login/", {
            "email": "a@x.com", "password": "testpass123",
        })
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn("access", resp.cookies)
        self.assertIn("refresh", resp.cookies)
        self.assertEqual(resp.cookies["refresh"]["path"], "/api/v1/auth/")

    def test_login_rejects_bad_password(self):
        resp = self.client.post("/api/v1/auth/login/", {
            "email": "a@x.com", "password": "wrong",
        })
        self.assertEqual(resp.status_code, 401)

    def test_me_requires_auth(self):
        resp = self.client.get("/api/v1/auth/me/")
        self.assertIn(resp.status_code, (401, 403))

    def test_me_reads_cookie(self):
        login = self.client.post("/api/v1/auth/login/", {
            "email": "a@x.com", "password": "testpass123",
        })
        self.client.cookies = login.cookies
        resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["email"], "a@x.com")

    def test_refresh_uses_cookie(self):
        login = self.client.post("/api/v1/auth/login/", {
            "email": "a@x.com", "password": "testpass123",
        })
        self.client.cookies = login.cookies
        resp = self.client.post("/api/v1/auth/refresh/")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn("access", resp.cookies)

    def test_logout_clears_cookies(self):
        login = self.client.post("/api/v1/auth/login/", {
            "email": "a@x.com", "password": "testpass123",
        })
        self.client.cookies = login.cookies
        resp = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(resp.status_code, 204)
        # delete_cookie sets max-age=0; value becomes empty
        self.assertIn(resp.cookies.get("access").value, ("", None))
