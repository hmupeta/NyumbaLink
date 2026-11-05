from django.db import connection
from django.http import JsonResponse


def health(request):
    checks = {"database": "ok"}
    status = 200
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        checks["database"] = "error"
        checks["detail"] = str(exc)
        status = 503
    return JsonResponse({"status": "ok" if status == 200 else "error", "checks": checks}, status=status)
