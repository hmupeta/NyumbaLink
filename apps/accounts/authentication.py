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
