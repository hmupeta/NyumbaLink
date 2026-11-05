import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from .managers import UserManager


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    username = None
    email = models.EmailField(
        unique=True,
        db_index=True,
    )
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
