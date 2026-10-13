"""Exact dashboard origins; public widget CORS has a separate policy."""

import os
from urllib.parse import urlsplit

_LOCAL_ORIGINS = [
    f"http://{host}:{port}"
    for host in ("localhost", "127.0.0.1")
    for port in (3000, 3001, 5173)
]


def dashboard_origins() -> list[str]:
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if not raw:
        if environment in {"production", "prod", "staging"}:
            raise RuntimeError(
                "CORS_ORIGINS requires exact frontend origins in deployment environments."
            )
        return list(_LOCAL_ORIGINS)
    origins = []
    for value in raw.split(","):
        value = value.strip()
        parsed = urlsplit(value)
        if (
            not value
            or value == "*"
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError(
                "CORS_ORIGINS accepts only exact HTTP(S) origins, never wildcards or URL paths."
            )
        try:
            parsed.port
        except ValueError as error:
            raise RuntimeError("CORS_ORIGINS contains an invalid port.") from error
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in origins:
            origins.append(origin)
    return origins
