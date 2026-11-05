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
