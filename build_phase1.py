#!/usr/bin/env python3
# NyumbaLink Phase 1 scaffold. Writes a runnable Django project.
# Usage: python build_phase1.py [--force] [--check]
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- pyproject

REQUIREMENTS = """
Django>=5.1,<5.2
djangorestframework>=3.15,<4.0
django-filter>=24.2
django-cors-headers>=4.3
drf-spectacular>=0.27
psycopg[binary]>=3.1
python-dotenv>=1.0
""".strip() + "\n"

REQUIREMENTS_DEV = """
-r requirements.txt
pytest>=8.0
pytest-django>=4.8
ruff>=0.4
""".strip() + "\n"

PYPROJECT = """
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "DJ"]
ignore = ["E501"]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.dev"
python_files = ["test_*.py"]
testpaths = ["apps"]
""".strip() + "\n"

GITIGNORE = """
__pycache__/
*.py[cod]
.venv/
venv/
.env
*.sqlite3
/media/
/staticfiles/
.pytest_cache/
.ruff_cache/
.DS_Store
""".strip() + "\n"

ENV_EXAMPLE = """
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=nyumbalink
DB_USER=nyumbalink
DB_PASSWORD=nyumbalink
DB_HOST=127.0.0.1
DB_PORT=5432

REDIS_URL=redis://127.0.0.1:6379/0
""".strip() + "\n"

DOCKER_COMPOSE = """
services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: nyumbalink
      POSTGRES_USER: nyumbalink
      POSTGRES_PASSWORD: nyumbalink
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U nyumbalink -d nyumbalink"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  pgdata:
""".strip() + "\n"

DOCKERFILE = """
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \\
    binutils libproj-dev gdal-bin libgdal-dev libgeos-dev libpq-dev \\
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
""".strip() + "\n"

CI_WORKFLOW = """
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      db:
        image: postgis/postgis:16-3.4
        env:
          POSTGRES_DB: nyumbalink
          POSTGRES_USER: nyumbalink
          POSTGRES_PASSWORD: nyumbalink
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U nyumbalink"
          --health-interval 5s --health-timeout 5s --health-retries 10
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    env:
      SECRET_KEY: ci-secret-key
      DB_NAME: nyumbalink
      DB_USER: nyumbalink
      DB_PASSWORD: nyumbalink
      DB_HOST: 127.0.0.1
      DB_PORT: "5432"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: System deps
        run: sudo apt-get update && sudo apt-get install -y gdal-bin libgdal-dev libgeos-dev
      - name: Install
        run: pip install -r requirements-dev.txt
      - name: Lint
        run: ruff check .
      - name: Migrations in sync
        run: python manage.py makemigrations --check --dry-run
      - name: Django check
        run: python manage.py check
      - name: Tests
        run: python manage.py test apps
""".strip() + "\n"

README = """
# NyumbaLink

Find your place. Connect your world.

## Quick start

    docker compose up -d
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements-dev.txt
    cp .env.example .env
    python manage.py migrate
    python manage.py seed_locations
    python manage.py createsuperuser
    python manage.py runserver

Open http://127.0.0.1:8000/api/docs/ and http://127.0.0.1:8000/health/

## Layout

    config/settings/{base,dev,prod}.py   split settings
    apps/accounts/                       custom User, UUID pk, email login
    apps/locations/                      Province > District > Locality > Neighbourhood
    apps/core/                           shared models, health check

## Conventions

- All primary keys are UUIDs.
- Email is the login identifier and is unique case-insensitively.
- Nothing is deleted that has financial or audit relevance.
- Credentials live in .env, never in settings.
""".strip() + "\n"

# ---------------------------------------------------------------- config

MANAGE_PY = """
#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Is it installed and is your virtualenv active?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
""".strip() + "\n"

CONFIG_INIT = ""

CONFIG_WSGI = """
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_wsgi_application()
""".strip() + "\n"

CONFIG_ASGI = """
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_asgi_application()
""".strip() + "\n"

SETTINGS_INIT = ""

SETTINGS_BASE = '''
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None, cast=str):
    value = os.environ.get(key, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    if cast is bool:
        return str(value).lower() in {"1", "true", "yes", "on"}
    return cast(value)


SECRET_KEY = env("SECRET_KEY", "dev-only-insecure-key")
DEBUG = env("DEBUG", "False", bool)
ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.locations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": env("DB_NAME", "nyumbalink"),
        "USER": env("DB_USER", "nyumbalink"),
        "PASSWORD": env("DB_PASSWORD", "nyumbalink"),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-zm"
TIME_ZONE = "Africa/Lusaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "NyumbaLink API",
    "DESCRIPTION": "Property discovery, verification and management for Zambia.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", "redis://127.0.0.1:6379/0"),
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
'''.strip() + "\n"

SETTINGS_DEV = '''
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_ORIGINS = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
'''.strip() + "\n"

SETTINGS_PROD = '''
from .base import *  # noqa: F401,F403

DEBUG = False

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True

CORS_ALLOWED_ORIGINS = [
    o.strip() for o in env("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
]
'''.strip() + "\n"

CONFIG_URLS = '''
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/v1/", include("apps.locations.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
'''.strip() + "\n"

# ---------------------------------------------------------------- core

APPS_INIT = ""

CORE_INIT = ""

CORE_APPS = '''
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
'''.strip() + "\n"

CORE_MODELS = '''
import uuid

from django.db import models


class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]
'''.strip() + "\n"

CORE_VIEWS = '''
from django.db import connection
from django.http import JsonResponse


def health(request):
    checks = {"database": "ok", "postgis": "ok"}
    status = 200
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.execute("SELECT PostGIS_Version()")
            cursor.fetchone()
    except Exception as exc:
        checks["database"] = "error"
        checks["postgis"] = "error"
        checks["detail"] = str(exc)
        status = 503
    return JsonResponse({"status": "ok" if status == 200 else "error", "checks": checks}, status=status)
'''.strip() + "\n"

# ---------------------------------------------------------------- accounts

ACCOUNTS_INIT = ""

ACCOUNTS_APPS = '''
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
'''.strip() + "\n"

ACCOUNTS_MANAGERS = '''
from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    def _normalize(self, email):
        # normalize_email() only lowercases the domain part.
        return self.normalize_email(email).lower()

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required")
        user = self.model(email=self._normalize(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)
'''.strip() + "\n"

ACCOUNTS_MODELS = '''
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    username = None
    email = models.EmailField(db_index=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    phone_verified_at = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="uniq_user_email_lower"),
        ]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email
'''.strip() + "\n"

ACCOUNTS_ADMIN = '''
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class NyumbaLinkUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)


class NyumbaLinkUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = NyumbaLinkUserChangeForm
    add_form = NyumbaLinkUserCreationForm
    ordering = ("email",)
    list_display = ("email", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email",)
    readonly_fields = ("last_login", "date_joined")
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Contact", {"fields": ("phone_number", "phone_verified_at")}),
        ("Permissions", {"fields": (
            "is_active", "is_staff", "is_superuser", "groups", "user_permissions",
        )}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
'''.strip() + "\n"

ACCOUNTS_TESTS = '''
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User


class UserManagerTests(TestCase):
    def test_create_user_normalises_email(self):
        user = User.objects.create_user(email="A@Example.COM", password="pw")
        self.assertEqual(user.email, "a@example.com")
        self.assertTrue(user.check_password("pw"))
        self.assertFalse(user.is_staff)

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pw")

    def test_email_uniqueness_is_case_insensitive(self):
        User.objects.create_user(email="a@example.com", password="pw")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="A@Example.com", password="pw")

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="pw")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_active)

    def test_string_representation(self):
        user = User.objects.create_user(email="b@example.com", password="pw")
        self.assertEqual(str(user), "b@example.com")
'''.strip() + "\n"

# ---------------------------------------------------------------- locations

LOCATIONS_INIT = ""

LOCATIONS_APPS = '''
from django.apps import AppConfig


class LocationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.locations"
    label = "locations"
'''.strip() + "\n"

LOCATIONS_MODELS = '''
from django.contrib.gis.db import models

from apps.core.models import TimeStampedModel


class Province(TimeStampedModel):
    name = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=64, unique=True)
    code = models.CharField(max_length=4, unique=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "province"
        verbose_name_plural = "provinces"

    def __str__(self):
        return self.name


class District(TimeStampedModel):
    province = models.ForeignKey(Province, on_delete=models.PROTECT, related_name="districts")
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "district"
        verbose_name_plural = "districts"
        constraints = [
            models.UniqueConstraint(fields=["province", "slug"], name="uniq_district_slug_per_province"),
        ]

    def __str__(self):
        return f"{self.name}, {self.province.name}"


class Locality(TimeStampedModel):
    district = models.ForeignKey(District, on_delete=models.PROTECT, related_name="localities")
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=64)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "locality"
        verbose_name_plural = "localities"
        constraints = [
            models.UniqueConstraint(fields=["district", "slug"], name="uniq_locality_slug_per_district"),
        ]

    def __str__(self):
        return f"{self.name}, {self.district.name}"


class Neighbourhood(TimeStampedModel):
    locality = models.ForeignKey(Locality, on_delete=models.PROTECT, related_name="neighbourhoods")
    name = models.CharField(max_length=96)
    slug = models.SlugField(max_length=96)
    aliases = models.JSONField(default=list, blank=True)
    centroid = models.PointField(srid=4326, null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "neighbourhood"
        verbose_name_plural = "neighbourhoods"
        constraints = [
            models.UniqueConstraint(fields=["locality", "slug"], name="uniq_neighbourhood_slug_per_locality"),
        ]

    def __str__(self):
        return f"{self.name}, {self.locality.name}"
'''.strip() + "\n"

LOCATIONS_ADMIN = '''
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import District, Locality, Neighbourhood, Province


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "slug")
    search_fields = ("name", "code")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "province", "slug")
    list_filter = ("province",)
    search_fields = ("name",)
    autocomplete_fields = ("province",)


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "slug")
    list_filter = ("district__province",)
    search_fields = ("name",)
    autocomplete_fields = ("district",)


@admin.register(Neighbourhood)
class NeighbourhoodAdmin(GISModelAdmin):
    list_display = ("name", "locality", "slug")
    list_filter = ("locality__district__province",)
    search_fields = ("name",)
    autocomplete_fields = ("locality",)
'''.strip() + "\n"

LOCATIONS_SERIALIZERS = '''
from rest_framework import serializers

from .models import District, Locality, Neighbourhood, Province


class ProvinceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Province
        fields = ("id", "name", "slug", "code")


class DistrictSerializer(serializers.ModelSerializer):
    province_name = serializers.CharField(source="province.name", read_only=True)

    class Meta:
        model = District
        fields = ("id", "name", "slug", "province", "province_name")


class LocalitySerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = Locality
        fields = ("id", "name", "slug", "district", "district_name")


class NeighbourhoodSerializer(serializers.ModelSerializer):
    locality_name = serializers.CharField(source="locality.name", read_only=True)

    class Meta:
        model = Neighbourhood
        fields = ("id", "name", "slug", "locality", "locality_name", "aliases")
'''.strip() + "\n"

LOCATIONS_VIEWS = '''
from rest_framework import viewsets

from .models import District, Locality, Neighbourhood, Province
from .serializers import (
    DistrictSerializer,
    LocalitySerializer,
    NeighbourhoodSerializer,
    ProvinceSerializer,
)


class ProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Province.objects.all().order_by("name")
    serializer_class = ProvinceSerializer
    search_fields = ("name", "code")
    lookup_field = "slug"


class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = District.objects.select_related("province").order_by("name")
    serializer_class = DistrictSerializer
    filterset_fields = ("province",)
    search_fields = ("name",)
    lookup_field = "slug"


class LocalityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Locality.objects.select_related("district").order_by("name")
    serializer_class = LocalitySerializer
    filterset_fields = ("district",)
    search_fields = ("name",)
    lookup_field = "slug"


class NeighbourhoodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Neighbourhood.objects.select_related("locality").order_by("name")
    serializer_class = NeighbourhoodSerializer
    filterset_fields = ("locality",)
    search_fields = ("name",)
    lookup_field = "slug"
'''.strip() + "\n"

LOCATIONS_URLS = '''
from rest_framework.routers import DefaultRouter

from .views import DistrictViewSet, LocalityViewSet, NeighbourhoodViewSet, ProvinceViewSet

router = DefaultRouter()
router.register("provinces", ProvinceViewSet, basename="province")
router.register("districts", DistrictViewSet, basename="district")
router.register("localities", LocalityViewSet, basename="locality")
router.register("neighbourhoods", NeighbourhoodViewSet, basename="neighbourhood")

urlpatterns = router.urls
'''.strip() + "\n"

LOCATIONS_TESTS = '''
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
'''.strip() + "\n"

SEED_COMMAND = '''
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.locations.models import District, Locality, Neighbourhood, Province

# NOTE: Province names are authoritative. District lists are indicative and MUST be
# reconciled against the official ECZ / 2022 census district list before public launch.
PROVINCES = [
    ("Central", "CE"),
    ("Copperbelt", "CB"),
    ("Eastern", "EA"),
    ("Luapula", "LP"),
    ("Lusaka", "LS"),
    ("Muchinga", "MC"),
    ("Northern", "NO"),
    ("North-Western", "NW"),
    ("Southern", "SO"),
    ("Western", "WE"),
]

DISTRICTS = {
    "Central": ["Chibombo", "Chisamba", "Chitambo", "Kabwe", "Kapiri Mposhi", "Luano",
                "Mkushi", "Mumbwa", "Ngabwe", "Serenje", "Shibuyunji"],
    "Copperbelt": ["Chililabombwe", "Chingola", "Kalulushi", "Kitwe", "Luanshya",
                   "Lufwanyama", "Masaiti", "Mpongwe", "Mufulira", "Ndola"],
    "Eastern": ["Chadiza", "Chama", "Chipata", "Kasenengwa", "Katete", "Lundazi",
                "Mambwe", "Nyimba", "Petauke", "Sinda", "Vubwi"],
    "Luapula": ["Chembe", "Chiengi", "Chifunabuli", "Chipili", "Kawambwa", "Lunga",
                "Mansa", "Milenge", "Mwansabombwe", "Mwense", "Nchelenge", "Samfya"],
    "Lusaka": ["Chilanga", "Chongwe", "Kafue", "Luangwa", "Lusaka", "Rufunsa"],
    "Muchinga": ["Chinsali", "Isoka", "Mafinga", "Mpika", "Nakonde", "Shiwang'andu"],
    "Northern": ["Chilubi", "Kaputa", "Kasama", "Luwingu", "Mbala", "Mporokoso",
                 "Mpulungu", "Mungwi", "Nsama", "Senga Hill"],
    "North-Western": ["Chavuma", "Kabompo", "Kalumbila", "Kasempa", "Manyinga",
                      "Mufumbwe", "Mushindamo", "Mwinilunga", "Solwezi", "Zambezi"],
    "Southern": ["Chikankata", "Choma", "Gwembe", "Itezhi-Tezhi", "Kalomo", "Kazungula",
                 "Livingstone", "Mazabuka", "Monze", "Namwala", "Pemba", "Siavonga",
                 "Sinazongwe", "Zimba"],
    "Western": ["Kalabo", "Kaoma", "Limulunga", "Lukulu", "Mongu", "Mulobezi", "Mwandi",
                "Nalolo", "Nkeyema", "Senanga", "Sesheke", "Shangombo", "Sioma"],
}

# Phase 1 seeds only Lusaka's neighbourhoods; the rest arrive with Phase 2 demand.
LUSAKA_NEIGHBOURHOODS = [
    "Kabulonga", "Woodlands", "Kabwata", "Chelston", "Roma", "Rhodes Park",
    "Ibex Hill", "Kalundu", "Olympia", "Emmasdale", "Matero", "Kalingalinga",
    "Chilenje", "Libala", "Avondale", "Meanwood", "Northmead", "Kamwala",
    "Fairview", "Thornpark", "Garden", "Chudleigh", "Silverest", "Chalala",
    "John Laing", "Mtendere", "Kaunda Square", "Chainda", "Bauleni",
]


class Command(BaseCommand):
    help = "Seed Zambian provinces, districts, localities and Lusaka neighbourhoods."

    def handle(self, *args, **options):
        created = {"province": 0, "district": 0, "locality": 0, "neighbourhood": 0}

        for name, code in PROVINCES:
            province, was_created = Province.objects.get_or_create(
                slug=slugify(name), defaults={"name": name, "code": code}
            )
            created["province"] += int(was_created)

            for district_name in DISTRICTS.get(name, []):
                district, was_created = District.objects.get_or_create(
                    province=province,
                    slug=slugify(district_name),
                    defaults={"name": district_name},
                )
                created["district"] += int(was_created)

                # One locality per district for now; finer granularity comes later.
                locality, was_created = Locality.objects.get_or_create(
                    district=district,
                    slug=slugify(district_name),
                    defaults={"name": district_name},
                )
                created["locality"] += int(was_created)

                if district_name == "Lusaka":
                    for hood_name in LUSAKA_NEIGHBOURHOODS:
                        _, was_created = Neighbourhood.objects.get_or_create(
                            locality=locality,
                            slug=slugify(hood_name),
                            defaults={"name": hood_name},
                        )
                        created["neighbourhood"] += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded: {province} provinces, {district} districts, "
                "{locality} localities, {neighbourhood} neighbourhoods.".format(**created)
            )
        )
'''.strip() + "\n"

# ---------------------------------------------------------------- manifest

FILES = {
    "requirements.txt": REQUIREMENTS,
    "requirements-dev.txt": REQUIREMENTS_DEV,
    "pyproject.toml": PYPROJECT,
    ".gitignore": GITIGNORE,
    ".env.example": ENV_EXAMPLE,
    "docker-compose.yml": DOCKER_COMPOSE,
    "Dockerfile": DOCKERFILE,
    "README.md": README,
    ".github/workflows/ci.yml": CI_WORKFLOW,
    "manage.py": MANAGE_PY,
    "config/__init__.py": CONFIG_INIT,
    "config/urls.py": CONFIG_URLS,
    "config/wsgi.py": CONFIG_WSGI,
    "config/asgi.py": CONFIG_ASGI,
    "config/settings/__init__.py": SETTINGS_INIT,
    "config/settings/base.py": SETTINGS_BASE,
    "config/settings/dev.py": SETTINGS_DEV,
    "config/settings/prod.py": SETTINGS_PROD,
    "apps/__init__.py": APPS_INIT,
    "apps/core/__init__.py": CORE_INIT,
    "apps/core/apps.py": CORE_APPS,
    "apps/core/models.py": CORE_MODELS,
    "apps/core/views.py": CORE_VIEWS,
    "apps/accounts/__init__.py": ACCOUNTS_INIT,
    "apps/accounts/apps.py": ACCOUNTS_APPS,
    "apps/accounts/managers.py": ACCOUNTS_MANAGERS,
    "apps/accounts/models.py": ACCOUNTS_MODELS,
    "apps/accounts/admin.py": ACCOUNTS_ADMIN,
    "apps/accounts/migrations/__init__.py": "",
    "apps/accounts/tests/__init__.py": "",
    "apps/accounts/tests/test_models.py": ACCOUNTS_TESTS,
    "apps/locations/__init__.py": LOCATIONS_INIT,
    "apps/locations/apps.py": LOCATIONS_APPS,
    "apps/locations/models.py": LOCATIONS_MODELS,
    "apps/locations/admin.py": LOCATIONS_ADMIN,
    "apps/locations/serializers.py": LOCATIONS_SERIALIZERS,
    "apps/locations/views.py": LOCATIONS_VIEWS,
    "apps/locations/urls.py": LOCATIONS_URLS,
    "apps/locations/migrations/__init__.py": "",
    "apps/locations/tests/__init__.py": "",
    "apps/locations/tests/test_locations.py": LOCATIONS_TESTS,
    "apps/locations/management/__init__.py": "",
    "apps/locations/management/commands/__init__.py": "",
    "apps/locations/management/commands/seed_locations.py": SEED_COMMAND,
    "apps/core/migrations/__init__.py": "",
}


def write_files(root: Path, force: bool) -> list[str]:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold NyumbaLink Phase 1.")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    parser.add_argument("--check", action="store_true", help="run manage.py check afterwards")
    parser.add_argument("--dir", default=".", help="target directory (default: cwd)")
    args = parser.parse_args()

    root = Path(args.dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    written, skipped = write_files(root, args.force)

    print(f"NyumbaLink Phase 1 -> {root}")
    print(f"  {len(written)} files written, {len(skipped)} skipped")
    for path in skipped:
        print(f"    skipped (exists, use --force): {path}")

    if args.check:
        print("\nRunning manage.py check ...")
        result = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=root,
            env={**__import__("os").environ, "DJANGO_SETTINGS_MODULE": "config.settings.dev"},
        )
        if result.returncode != 0:
            print("\ncheck failed. Most likely cause: GDAL/GEOS missing, "
                  "or PostgreSQL not running. See the notes below.")
            return result.returncode

    print(
        "\nNext steps (manual):\n"
        "  1. docker compose up -d\n"
        "  2. python -m venv .venv && source .venv/bin/activate\n"
        "  3. pip install -r requirements-dev.txt\n"
        "  4. cp .env.example .env\n"
        "  5. python manage.py makemigrations accounts locations\n"
        "  6. READ the generated migration, then: python manage.py migrate\n"
        "  7. python manage.py seed_locations\n"
        "  8. python manage.py createsuperuser\n"
        "  9. python manage.py test apps\n"
        " 10. python manage.py runserver\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())