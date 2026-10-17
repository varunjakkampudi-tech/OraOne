"""Single registry of the environment keys the backend reads.

Every key the application reads from the process environment (or from
``backend/.env``) is listed here once. The admin configuration console, the
startup override loader and the masking rules all read from this module, so
they cannot drift apart.

Rules for entries:
  * ``kind="secret"`` values are never returned in full by any API. The API
    returns only set / not set and, when the value is long enough, a masked
    tail of at most four characters.
  * ``console_managed=False`` keys are shown read-only. They are bootstrap or
    process-level settings (database location, signing keys, environment name,
    worker and gunicorn tuning). Changing them from a web request could lock
    the platform out or break decryption, so they stay in the deployment's
    secret store or ``backend/.env``.
  * ``environments`` lists where the key applies. Keys that a production-like
    deployment refuses to run with are marked ``required``.

Do not add keys the code does not read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

LOCAL = "local"
PRODUCTION = "production"
ENVIRONMENTS: tuple[str, ...] = (LOCAL, PRODUCTION)

# Values from app.core.config that mean "treat as production".
PRODUCTION_LIKE_ENVIRONMENTS = frozenset({"production", "prod", "staging"})

GROUPS: tuple[str, ...] = (
    "Core",
    "Database",
    "Auth and email",
    "AI models",
    "WhatsApp",
    "Instagram",
    "Twilio",
    "Voice",
    "Google",
    "Marketing email",
    "Widget",
    "Limits",
)

# A masked tail is shown only for values long enough that four characters do
# not reveal a meaningful part of the secret.
_MIN_LENGTH_FOR_TAIL = 12
_TAIL_LENGTH = 4


@dataclass(frozen=True)
class ConfigKey:
    name: str
    group: str
    kind: Literal["secret", "plain"]
    required: bool
    description: str
    environments: tuple[str, ...] = ENVIRONMENTS
    console_managed: bool = True


def _key(
    name: str,
    group: str,
    description: str,
    *,
    secret: bool = False,
    required: bool = False,
    environments: tuple[str, ...] = ENVIRONMENTS,
    console_managed: bool = True,
) -> ConfigKey:
    return ConfigKey(
        name=name,
        group=group,
        kind="secret" if secret else "plain",
        required=required,
        description=description,
        environments=environments,
        console_managed=console_managed,
    )


REGISTRY: tuple[ConfigKey, ...] = (
    # ---- Core -------------------------------------------------------------
    _key(
        "ENVIRONMENT",
        "Core",
        "Deployment name. development, local, staging, prod or production. Production-like names turn on strict startup checks.",
        console_managed=False,
    ),
    _key(
        "LOG_LEVEL",
        "Core",
        "Minimum log level for the API process, for example INFO or DEBUG.",
    ),
    _key(
        "ORAONE_VERSION",
        "Core",
        "Version label shown in health and operations pages.",
    ),
    _key(
        "FRONTEND_URL",
        "Core",
        "Public web address of the frontend. Used in links inside emails and redirects.",
    ),
    _key(
        "APP_URL",
        "Core",
        "Address the signed-in app returns to after billing and team invitation flows.",
    ),
    _key(
        "BACKEND_PUBLIC_URL",
        "Core",
        "Public address of the API. Used to build widget and branding asset URLs. Checked before the other backend URL settings.",
    ),
    _key(
        "PUBLIC_BACKEND_URL",
        "Core",
        "Fallback public address of the API for widget and branding URLs, used when BACKEND_PUBLIC_URL is not set.",
    ),
    _key(
        "BACKEND_URL",
        "Core",
        "Last-resort fallback public address of the API for widget and branding URLs.",
    ),
    _key(
        "CORS_ORIGINS",
        "Core",
        "Comma-separated list of web origins allowed to call the API. Production requires exact origins.",
        required=True,
    ),
    _key(
        "TRUSTED_PROXY_IPS",
        "Core",
        "Comma-separated proxy addresses whose forwarded client IP headers are trusted for rate limiting.",
    ),
    _key(
        "UPLOAD_DIR",
        "Core",
        "Folder on the API server where uploaded documents are stored.",
    ),
    _key(
        "RUN_BACKGROUND_WORKERS",
        "Core",
        "When true, the API process also runs the workflow scheduler and webhook outbox. Production runs these in the worker process instead.",
        console_managed=False,
    ),
    _key(
        "METRICS_BACKEND",
        "Core",
        "Where metrics are sent: inprocess, prometheus or otel.",
    ),
    _key(
        "ENTITLEMENTS_CACHE_BACKEND",
        "Core",
        "Cache used for plan entitlements: inprocess or redis.",
    ),
    _key(
        "REDIS_URL",
        "Core",
        "Connection address of the shared Redis cache. Required in production so that rate limits and refresh tokens are shared across workers.",
        secret=True,
        required=True,
    ),
    _key(
        "OTEL_SERVICE_NAME",
        "Core",
        "Service name attached to traces sent to the tracing collector.",
    ),
    _key(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "Core",
        "Tracing collector address. Tracing stays off when this is empty.",
    ),
    _key(
        "STRIPE_SECRET_KEY",
        "Core",
        "Stripe secret key for billing. Leave empty to keep billing in free-access mode.",
        secret=True,
    ),
    _key(
        "STRIPE_WEBHOOK_SECRET",
        "Core",
        "Signing secret for Stripe webhooks. Webhooks are refused when this is empty.",
        secret=True,
    ),
    _key(
        "GUNICORN_WORKERS",
        "Core",
        "Number of Gunicorn worker processes in production.",
        environments=(PRODUCTION,),
        console_managed=False,
    ),
    _key(
        "GUNICORN_TIMEOUT_SECONDS",
        "Core",
        "Seconds before a silent Gunicorn worker is restarted.",
        environments=(PRODUCTION,),
        console_managed=False,
    ),
    _key(
        "GUNICORN_GRACEFUL_TIMEOUT_SECONDS",
        "Core",
        "Seconds Gunicorn waits for in-flight requests during a restart.",
        environments=(PRODUCTION,),
        console_managed=False,
    ),
    _key(
        "GUNICORN_KEEPALIVE_SECONDS",
        "Core",
        "Keep-alive seconds for idle client connections on Gunicorn.",
        environments=(PRODUCTION,),
        console_managed=False,
    ),
    _key(
        "GUNICORN_MAX_REQUESTS",
        "Core",
        "Requests a Gunicorn worker serves before it is recycled.",
        environments=(PRODUCTION,),
        console_managed=False,
    ),
    _key(
        "GUNICORN_MAX_REQUESTS_JITTER",
        "Core",
        "Random spread added to the recycle count so workers do not restart together.",
        environments=(PRODUCTION,),
        console_managed=False,
    ),
    _key(
        "GUNICORN_LOG_LEVEL",
        "Core",
        "Log level for the Gunicorn master process.",
        environments=(PRODUCTION,),
        console_managed=False,
    ),
    # ---- Database ---------------------------------------------------------
    _key(
        "DATABASE_URL",
        "Database",
        "Full PostgreSQL connection string. When set, the DB_* settings below are ignored.",
        secret=True,
        required=True,
        console_managed=False,
    ),
    _key(
        "ALEMBIC_DATABASE_URL",
        "Database",
        "PostgreSQL connection string used only by database migrations. Falls back to DATABASE_URL.",
        secret=True,
        console_managed=False,
    ),
    _key(
        "DB_HOST",
        "Database",
        "PostgreSQL host, used only when DATABASE_URL is not set.",
        console_managed=False,
    ),
    _key(
        "DB_PORT",
        "Database",
        "PostgreSQL port, used only when DATABASE_URL is not set. Default 5432.",
        console_managed=False,
    ),
    _key(
        "DB_USER",
        "Database",
        "PostgreSQL user name, used only when DATABASE_URL is not set.",
        console_managed=False,
    ),
    _key(
        "DB_PASSWORD",
        "Database",
        "PostgreSQL password, used only when DATABASE_URL is not set.",
        secret=True,
        console_managed=False,
    ),
    _key(
        "DB_NAME",
        "Database",
        "PostgreSQL database name, used only when DATABASE_URL is not set.",
        console_managed=False,
    ),
    # ---- Auth and email ---------------------------------------------------
    _key(
        "JWT_SECRET_KEY",
        "Auth and email",
        "Secret that signs session tokens. Must be at least 32 characters. Changing it signs everyone out.",
        secret=True,
        required=True,
        console_managed=False,
    ),
    _key(
        "SECRET_KEY",
        "Auth and email",
        "Fallback secret used to derive the integration encryption key when INTEGRATIONS_ENCRYPTION_KEY is not set.",
        secret=True,
        console_managed=False,
    ),
    _key(
        "INTEGRATIONS_ENCRYPTION_KEY",
        "Auth and email",
        "Key that encrypts stored integration tokens and console-managed configuration values. Changing it makes stored values unreadable.",
        secret=True,
        console_managed=False,
    ),
    _key(
        "JWT_ISSUER",
        "Auth and email",
        "Issuer name written into and required on session tokens.",
    ),
    _key(
        "JWT_ACCESS_TTL_MINUTES",
        "Auth and email",
        "How long an access token stays valid, in minutes. Default 15.",
    ),
    _key(
        "JWT_REFRESH_TTL_DAYS",
        "Auth and email",
        "How long a refresh token stays valid, in days. Default 30.",
    ),
    _key(
        "JWT_LEEWAY_SECONDS",
        "Auth and email",
        "Clock-skew allowance, in seconds, when checking token expiry. Default 60.",
    ),
    _key(
        "ALLOW_DEV_PASSWORD_LOGIN",
        "Auth and email",
        "Lets seeded development accounts sign in with a password. Refused in production.",
        environments=(LOCAL,),
    ),
    _key(
        "SMTP_HOST",
        "Auth and email",
        "Mail server host that sends sign-in codes and invitations.",
    ),
    _key(
        "SMTP_PORT",
        "Auth and email",
        "Mail server port. Default 587 when TLS is used.",
    ),
    _key(
        "SMTP_USER",
        "Auth and email",
        "User name for the mail server.",
    ),
    _key(
        "SMTP_PASSWORD",
        "Auth and email",
        "Password for the mail server.",
        secret=True,
    ),
    _key(
        "SMTP_FROM",
        "Auth and email",
        "Sender address on outgoing mail. Falls back to SMTP_USER.",
    ),
    _key(
        "SMTP_USE_SSL",
        "Auth and email",
        "Whether mail is sent over an encrypted connection. Set to false only for local test servers.",
    ),
    # ---- AI models --------------------------------------------------------
    _key(
        "OPENROUTER_API_KEY",
        "AI models",
        "API key for OpenRouter, the model provider used for AI replies and embeddings. Required for AI replies.",
        secret=True,
        required=True,
    ),
    _key(
        "OPENROUTER_BASE_URL",
        "AI models",
        "Base address of the OpenRouter API. Default https://openrouter.ai/api/v1.",
    ),
    _key(
        "OPENROUTER_MODEL",
        "AI models",
        "Default model identifier, in provider/model form, used when an agent does not choose one.",
    ),
    _key(
        "OPENROUTER_TIMEOUT",
        "AI models",
        "Seconds to wait for a model reply before giving up. Default 60.",
    ),
    _key(
        "OPENROUTER_SITE_URL",
        "AI models",
        "Site address sent to OpenRouter as the referring application.",
    ),
    _key(
        "OPENROUTER_APP_NAME",
        "AI models",
        "Application name sent to OpenRouter in requests.",
    ),
    _key(
        "AI_FORCE_MODEL",
        "AI models",
        "Pins every reply to one model, bypassing agent and organisation choices. Leave empty in normal operation.",
    ),
    _key(
        "AI_MAX_OUTPUT_TOKENS",
        "AI models",
        "Upper limit on the length of a model reply, in tokens. Default 2048.",
    ),
    _key(
        "EMBEDDING_MODEL",
        "AI models",
        "Model used to create knowledge embeddings. Default openai/text-embedding-3-small.",
    ),
    _key(
        "EMBED_DIM",
        "AI models",
        "Vector size of embeddings. Must match the database column; changing it needs a migration. Default 1024.",
        console_managed=False,
    ),
    _key(
        "EMBEDDING_TIMEOUT",
        "AI models",
        "Seconds to wait for an embedding request. Default 30.",
    ),
    _key(
        "RERANKER_PROVIDER",
        "AI models",
        "Search re-ranking provider: heuristic, cohere, jina or local. Default heuristic.",
    ),
    _key(
        "RERANK_HTTP_TIMEOUT",
        "AI models",
        "Seconds to wait for a re-ranking request. Default 8.",
    ),
    _key(
        "COHERE_API_KEY",
        "AI models",
        "API key for Cohere re-ranking. Used only when the re-ranker is set to cohere.",
        secret=True,
    ),
    _key(
        "COHERE_RERANK_MODEL",
        "AI models",
        "Cohere re-ranking model name.",
    ),
    _key(
        "JINA_API_KEY",
        "AI models",
        "API key for Jina re-ranking. Used only when the re-ranker is set to jina.",
        secret=True,
    ),
    _key(
        "JINA_RERANK_MODEL",
        "AI models",
        "Jina re-ranking model name.",
    ),
    _key(
        "BGE_RERANK_MODEL",
        "AI models",
        "Local re-ranking model name, run on the API server.",
    ),
    # ---- WhatsApp ---------------------------------------------------------
    _key(
        "META_WHATSAPP_ACCESS_TOKEN",
        "WhatsApp",
        "Meta access token that sends WhatsApp replies.",
        secret=True,
    ),
    _key(
        "META_WHATSAPP_APP_SECRET",
        "WhatsApp",
        "Meta app secret that verifies WhatsApp webhook signatures. Required when a Meta token is set.",
        secret=True,
    ),
    _key(
        "META_WHATSAPP_VERIFY_TOKEN",
        "WhatsApp",
        "Verification token used during Meta's webhook handshake.",
        secret=True,
    ),
    # ---- Instagram --------------------------------------------------------
    _key(
        "META_INSTAGRAM_ACCESS_TOKEN",
        "Instagram",
        "Page or Instagram-scoped Meta access token that sends Instagram direct messages. Webhook checks use the WhatsApp app secret.",
        secret=True,
    ),
    # ---- Twilio -----------------------------------------------------------
    _key(
        "TWILIO_ACCOUNT_SID",
        "Twilio",
        "Twilio account identifier for SMS and voice. Required with the auth token.",
    ),
    _key(
        "TWILIO_AUTH_TOKEN",
        "Twilio",
        "Twilio auth token. Used to send messages and to verify Twilio webhook signatures.",
        secret=True,
    ),
    _key(
        "TWILIO_PHONE_NUMBER",
        "Twilio",
        "Twilio phone number that sends SMS and places calls, in E.164 form.",
    ),
    _key(
        "PUBLIC_API_BASE_URL",
        "Twilio",
        "Exact public https address Twilio calls. Required with Twilio, because Twilio signs this exact URL.",
    ),
    # ---- Voice ------------------------------------------------------------
    _key(
        "VOICE_HANDOFF_NUMBER",
        "Voice",
        "Phone number in E.164 form that live calls are transferred to when the caller asks for a person.",
    ),
    _key(
        "VOICE_SAY_VOICE",
        "Voice",
        "Twilio voice used for spoken prompts. Default alice.",
    ),
    _key(
        "ELEVENLABS_API_KEY",
        "Voice",
        "ElevenLabs API key for natural-sounding voice replies. Voice falls back to the Twilio voice when empty.",
        secret=True,
    ),
    _key(
        "ELEVENLABS_VOICE_ID",
        "Voice",
        "ElevenLabs voice identifier. ElevenLabs is used only when both this and the API key are set.",
    ),
    _key(
        "ELEVENLABS_MODEL_ID",
        "Voice",
        "ElevenLabs speech model. Default eleven_flash_v2_5.",
    ),
    # ---- Google -----------------------------------------------------------
    _key(
        "GOOGLE_CLIENT_ID",
        "Google",
        "OAuth client identifier for the Google Drive connection.",
    ),
    _key(
        "GOOGLE_CLIENT_SECRET",
        "Google",
        "OAuth client secret for the Google Drive connection.",
        secret=True,
    ),
    _key(
        "GOOGLE_REDIRECT_URI",
        "Google",
        "Address Google returns to after consent. Must match the Google console entry exactly.",
    ),
    # ---- Marketing email --------------------------------------------------
    _key(
        "EMAIL_INBOUND_SECRET",
        "Marketing email",
        "Shared secret the email provider sends with inbound email webhooks. Every inbound email is refused when this is empty.",
        secret=True,
    ),
    # ---- Widget -----------------------------------------------------------
    _key(
        "WIDGET_API_BASE",
        "Widget",
        "Address the embeddable chat widget calls for its API. Overrides the backend URL fallbacks.",
    ),
    _key(
        "WIDGET_CDN_BASE",
        "Widget",
        "Address the widget script is loaded from. Defaults to FRONTEND_URL.",
    ),
    _key(
        "WIDGET_IP_RATE_LIMIT_PER_MIN",
        "Widget",
        "Widget requests allowed per client IP each minute. Default 60.",
    ),
    # ---- Limits -----------------------------------------------------------
    _key(
        "ORAONE_FREE_ACCESS_ONLY",
        "Limits",
        "When true, every organisation is on free access and paid plans are not enforced. Default true.",
    ),
    _key(
        "AUTHZ_ENFORCE_SUBSCRIPTION",
        "Limits",
        "When true, subscription status blocks protected features. Off by default.",
    ),
    _key(
        "AUTHZ_ENFORCE_QUOTAS",
        "Limits",
        "When true, usage quotas block requests once exceeded. Off by default.",
    ),
    _key(
        "RATE_LIMIT_AUTH_PER_MINUTE",
        "Limits",
        "Sign-in and code requests allowed per client each minute. Default 10.",
    ),
    _key(
        "RATE_LIMIT_AI_PER_MINUTE",
        "Limits",
        "AI requests allowed per client each minute. Default 20.",
    ),
    _key(
        "RATE_LIMIT_WEBHOOK_PER_MINUTE",
        "Limits",
        "Webhook deliveries accepted each minute. Default 600.",
    ),
    _key(
        "RATE_LIMIT_API_PER_MINUTE",
        "Limits",
        "General API requests allowed per client each minute. Default 120.",
    ),
)

BY_NAME: dict[str, ConfigKey] = {key.name: key for key in REGISTRY}

if len(BY_NAME) != len(REGISTRY):  # pragma: no cover - guards against typos
    raise RuntimeError("config_registry contains duplicate key names")


def runtime_environment(raw: Optional[str]) -> str:
    """Map the ENVIRONMENT value of this process to ``local`` or ``production``."""
    value = (raw or "").strip().lower()
    return PRODUCTION if value in PRODUCTION_LIKE_ENVIRONMENTS else LOCAL


def mask_secret(value: Optional[str]) -> Optional[str]:
    """Return the masked tail of a secret, at most four characters.

    Returns ``None`` when the value is empty or too short to show a tail
    safely. The full value never leaves this function.
    """
    if not value or len(value) < _MIN_LENGTH_FOR_TAIL:
        return None
    return value[-_TAIL_LENGTH:]
