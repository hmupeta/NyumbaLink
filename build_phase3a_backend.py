#!/usr/bin/env python3
"""NyumbaLink Phase 3a backend patch: JWT cookie auth + CORS for Vite."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------- files

AUTHENTICATION = '''
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTCookieAuthentication(JWTAuthentication):
    """JWT authentication that reads the access token from an httpOnly cookie.

    Falls back to the standard Authorization: Bearer header, so curl-based
    testing and the Swagger UI still work.
    """

    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw_token = request.COOKIES.get("access")
        if not raw_token:
            return None

        validated = self.get_validated_token(raw_token)
        return self.get_user(validated), validated
'''.strip() + "\n"

SERIALIZERS = '''
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "is_staff")
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value):
        normalised = value.lower()
        if User.objects.filter(email=normalised).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return normalised

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
'''.strip() + "\n"

VIEWS = '''
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, UserSerializer


def _cookie_kwargs(max_age: int) -> dict:
    return {
        "max_age": max_age,
        "httponly": True,
        "secure": not settings.DEBUG,
        "samesite": "Lax",
    }


def _set_auth_cookies(response, access: str, refresh: str) -> None:
    access_age = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
    refresh_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie("access", access, path="/", **_cookie_kwargs(access_age))
    # Refresh cookie scoped to the auth namespace only.
    response.set_cookie(
        "refresh", refresh, path="/api/v1/auth/", **_cookie_kwargs(refresh_age)
    )


def _clear_auth_cookies(response) -> None:
    response.delete_cookie("access", path="/")
    response.delete_cookie("refresh", path="/api/v1/auth/")


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        response = Response(
            {"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED
        )
        _set_auth_cookies(response, str(refresh.access_token), str(refresh))
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").lower().strip()
        password = request.data.get("password") or ""

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        response = Response({"user": UserSerializer(user).data})
        _set_auth_cookies(response, str(refresh.access_token), str(refresh))
        return response


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get("refresh") or request.data.get("refresh")
        if not raw:
            return Response(
                {"detail": "No refresh token provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            refresh = RefreshToken(raw)
        except TokenError:
            return Response(
                {"detail": "Refresh token invalid or expired."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = Response({"detail": "Refreshed."})
        _set_auth_cookies(response, str(refresh.access_token), str(refresh))
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_auth_cookies(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
'''.strip() + "\n"

URLS = '''
from django.urls import path

from .views import LoginView, LogoutView, MeView, RefreshView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
]
'''.strip() + "\n"

TESTS = '''
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
'''.strip() + "\n"

FILES = {
    "apps/accounts/authentication.py": AUTHENTICATION,
    "apps/accounts/serializers.py": SERIALIZERS,
    "apps/accounts/views.py": VIEWS,
    "apps/accounts/urls.py": URLS,
    "apps/accounts/tests/test_auth.py": TESTS,
}

# ---------------------------------------------------------------------- patches

PATCHES = [
    # requirements.txt
    (
        "requirements.txt",
        "drf-nested-routers>=0.94\n",
        "drf-nested-routers>=0.94\ndjangorestframework-simplejwt>=5.4\n",
        "requirements: add djangorestframework-simplejwt",
    ),
    # INSTALLED_APPS — add rest_framework_simplejwt
    (
        "config/settings/base.py",
        '    "drf_spectacular",\n',
        '    "drf_spectacular",\n    "rest_framework_simplejwt",\n',
        "settings: register rest_framework_simplejwt",
    ),
    # REST_FRAMEWORK auth classes
    (
        "config/settings/base.py",
        '    "DEFAULT_AUTHENTICATION_CLASSES": [\n'
        '        "rest_framework.authentication.SessionAuthentication",\n'
        '    ],\n',
        '    "DEFAULT_AUTHENTICATION_CLASSES": [\n'
        '        "apps.accounts.authentication.JWTCookieAuthentication",\n'
        '        "rest_framework_simplejwt.authentication.JWTAuthentication",\n'
        '        "rest_framework.authentication.SessionAuthentication",\n'
        '    ],\n',
        "settings: add JWT cookie auth class",
    ),
    # SIMPLE_JWT + CORS — append after SPECTACULAR_SETTINGS block
    (
        "config/settings/base.py",
        'CACHES = {\n',
        'SIMPLE_JWT = {\n'
        '    "ACCESS_TOKEN_LIFETIME": __import__("datetime").timedelta(minutes=15),\n'
        '    "REFRESH_TOKEN_LIFETIME": __import__("datetime").timedelta(days=7),\n'
        '    "ROTATE_REFRESH_TOKENS": True,\n'
        '    "AUTH_HEADER_TYPES": ("Bearer",),\n'
        '}\n'
        '\n'
        'CORS_ALLOW_CREDENTIALS = True\n'
        'CORS_ALLOWED_ORIGINS = [\n'
        '    "http://localhost:5173",\n'
        '    "http://127.0.0.1:5173",\n'
        ']\n'
        'CSRF_TRUSTED_ORIGINS = [\n'
        '    "http://localhost:5173",\n'
        '    "http://127.0.0.1:5173",\n'
        ']\n'
        '\n'
        'CACHES = {\n',
        "settings: SIMPLE_JWT, CORS, CSRF trusted origins",
    ),
    # urls.py — mount auth
    (
        "config/urls.py",
        'path("api/v1/", include("apps.properties.urls")),\n',
        'path("api/v1/", include("apps.properties.urls")),\n'
        '    path("api/v1/auth/", include("apps.accounts.urls")),\n',
        "urls: mount apps.accounts.urls under /api/v1/auth/",
    ),
]

# ---------------------------------------------------------------------- engine


def write_files(root: Path, force: bool) -> tuple[list[str], list[str]]:
    written, skipped = [], []
    for relative, content in FILES.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not force and target.read_text(encoding="utf-8") != content:
            skipped.append(relative)
            continue
        target.write_text(content, encoding="utf-8")
        written.append(relative)
    return written, skipped


def apply_patch(root: Path, relative: str, old: str, new: str, desc: str) -> str:
    path = root / relative
    if not path.exists():
        return f"  SKIP   {desc}  (missing: {relative})"
    text = path.read_text(encoding="utf-8")
    if old not in text:
        marker = new.strip().split("\n")[0]
        if marker in text:
            return f"  ok     {desc}  (already applied)"
        return f"  WARN   {desc}  (snippet not found in {relative})"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"  PATCH  {desc}"


def run_manage(root: Path, *args: str) -> int:
    return subprocess.run(
        [sys.executable, "manage.py", *args], cwd=root
    ).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold Phase 3a backend.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dir", default=".")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    if not (root / "manage.py").exists():
        print(f"No manage.py in {root}. Run from project root.")
        return 1

    print(f"NyumbaLink Phase 3a (backend) -> {root}\n")
    written, skipped = write_files(root, args.force)
    print(f"Files: {len(written)} written, {len(skipped)} skipped")
    for path in skipped:
        print(f"  skipped (use --force to overwrite): {path}")

    print("\nPatching existing files:")
    results = [apply_patch(root, *p) for p in PATCHES]
    print("\n".join(results))

    if any(r.startswith("  WARN") for r in results):
        print("\nSome patches did not match — inspect those files by hand.")

    if args.check:
        rc = run_manage(root, "check")
        if rc != 0:
            print("\ncheck failed — likely simplejwt not installed yet.")
            return rc

    print("""
Next steps:

  1.  .\\venv\\Scripts\\python.exe -m pip install -r requirements.txt
      (installs djangorestframework-simplejwt)

  2.  .\\venv\\Scripts\\python.exe manage.py check
      expected: System check identified no issues (0 silenced).

  3.  .\\venv\\Scripts\\python.exe manage.py test apps.accounts
      expected: Ran 14 tests ... OK
      (5 Phase-1 user tests + 9 new auth tests)

  4.  .\\venv\\Scripts\\python.exe manage.py test apps
      expected: Ran 33 tests ... OK

  5.  Manual smoke test:
        .\\venv\\Scripts\\python.exe manage.py runserver
      In a second terminal:
        curl -c cookies.txt -X POST http://127.0.0.1:8000/api/v1/auth/login/ ^
             -H "Content-Type: application/json" ^
             -d "{\\"email\\":\\"<your superuser email>\\",\\"password\\":\\"<password>\\"}"
        curl -b cookies.txt http://127.0.0.1:8000/api/v1/auth/me/
      Second call should return your user record.

  6.  git add -A
      git commit -m "Phase 3a: JWT cookie auth + CORS for Vite dev"
      (do NOT tag yet — tag at end of Phase 3a once frontend is verified)

Frontend scaffold follows in the next message after these tests pass.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())