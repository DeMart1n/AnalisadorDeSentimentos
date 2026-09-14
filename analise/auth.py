import jwt
from datetime import datetime, timezone, timedelta
from functools import wraps
from django.conf import settings
from django.http import JsonResponse
from .models import Users

ALGORITHM = "HS256"
ACCESS_TOKEN_LIFETIME = timedelta(hours=1)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)
JWT_SECRET = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)


def token_generator(user: Users) -> tuple[str, str]:
    access_payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + ACCESS_TOKEN_LIFETIME,
        "iat": datetime.now(timezone.utc),
    }
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=ALGORITHM)

    refresh_payload = {
        "user_id": user.id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + REFRESH_TOKEN_LIFETIME,
        "iat": datetime.now(timezone.utc),
    }
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=ALGORITHM)

    return access_token, refresh_token


def jwt_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({"erro": "Invalid token"}, status=401)

        partes = auth_header.split(" ")
        if len(partes) != 2:
            return JsonResponse({"erro": "Invalid token"}, status=401)

        token = partes[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
            if payload.get("type") != "access":
                return JsonResponse({"erro": "Invalid token"}, status=401)

            request.user_id = payload["user_id"]
            request.user_role = payload["role"]
        except jwt.ExpiredSignatureError:
            return JsonResponse({"erro": "Token Expired"}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({"erro": "Invalid token"}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper

def admin_required(view_func):
    @jwt_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if getattr(request, "user_role", None) != "ADMIN":
            return JsonResponse({"erro": "Acesso negado."}, status=403)
        return view_func(request, *args, **kwargs)

    return wrapper
