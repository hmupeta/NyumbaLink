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
        "samesite": "None" if not settings.DEBUG else "Lax",
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
            {"user": UserSerializer(user).data, "access": str(refresh.access_token), "refresh": str(refresh)}, status=status.HTTP_201_CREATED
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
        response = Response({"user": UserSerializer(user).data, "access": str(refresh.access_token), "refresh": str(refresh)})
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

    def patch(self, request):
        user = request.user
        for field in ["first_name", "last_name", "bio"]:
            if field in request.data:
                setattr(user, field, request.data[field])
        if "avatar" in request.FILES:
            user.avatar = request.FILES["avatar"]
        if "cover_photo" in request.FILES:
            user.cover_photo = request.FILES["cover_photo"]
        user.save()
        return Response(UserSerializer(user).data)


# ---------- PASSWORD RESET ----------
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings as django_settings
from .models import User as UserModel


class PasswordResetRequestView(APIView):
    """Step 1: User submits email. We send a reset link with a short-lived token."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").lower().strip()
        if not email:
            return Response({"detail": "Email is required."}, status=400)

        user = UserModel.objects.filter(email=email).first()
        
        # Always return 200 to prevent email enumeration attacks.
        if not user:
            return Response({"detail": "If the email exists, a reset link has been sent."}, status=200)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{request.data.get('origin', 'http://localhost:5173')}/reset-password/{uid}/{token}"

        subject = "Reset your NyumbaLink password"
        message = f"""
Hello {user.first_name or user.email},

Someone requested a password reset for your NyumbaLink account.
If this was you, click the link below to set a new password:

{reset_url}

This link expires in 1 hour. If you didn't request this, you can safely ignore this email.

— The NyumbaLink Team
        """.strip()

        try:
            send_mail(subject, message, django_settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
        except Exception:
            pass  # Silent fail — email issues shouldn't leak account existence

        return Response({"detail": "If the email exists, a reset link has been sent."}, status=200)


class PasswordResetConfirmView(APIView):
    """Step 2: User submits uid + token + new password from the email link."""
    permission_classes = [AllowAny]

    def post(self, request):
        uid_b64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("password")

        if not all([uid_b64, token, new_password]):
            return Response({"detail": "Missing fields."}, status=400)

        if len(new_password) < 8:
            return Response({"detail": "Password must be at least 8 characters."}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uid_b64))
            user = UserModel.objects.get(pk=uid)
        except (UserModel.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Invalid reset link."}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "This reset link has expired or is invalid."}, status=400)

        user.set_password(new_password)
        user.save()

        return Response({"detail": "Password reset successfully. Please log in."}, status=200)
