"""Speech for voice replies: ElevenLabs when configured, Twilio's built-in voice otherwise.

Each spoken turn becomes one TwiML verb:

* :class:`TwilioSayProvider` returns ``<Say>`` using the configured Twilio voice. It is
  always available and is the fallback for every failure.
* :class:`ElevenLabsProvider` synthesises MP3 through the ElevenLabs text-to-speech REST
  API, caches the audio briefly and returns a ``<Play>`` URL pointing at
  ``/api/voice/audio/{key}.mp3``. Twilio fetches that URL, so the public API base URL
  must be configured.

ElevenLabs is used only when both ``ELEVENLABS_API_KEY`` and ``ELEVENLABS_VOICE_ID`` are
set. Any failure for a turn (HTTP error, timeout, missing public URL, cache error) falls
back to ``<Say>`` for that turn. Logs record status codes and exception type names only:
never the API key, the audio, or the spoken text.

Audio cache: entries live for ``AUDIO_TTL_SECONDS`` and at most
``AUDIO_CACHE_MAX_ENTRIES`` per process. Keys are HMAC-SHA256 over the voice id and text,
keyed with the API key, so they cannot be guessed without that secret. Multi-worker
deployments need the shared path: when ``REDIS_URL`` is set, audio is stored in Redis
through :func:`app.services.cache.get_shared_cache` so any worker can serve it. Without
Redis, a `<Play>` request that reaches a different worker gets a 404 and that turn is
silent, so set ``REDIS_URL`` for multi-worker voice deployments.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Callable, Optional

import httpx

from app.services.voice import twiml

log = logging.getLogger("app.voice.tts")

AUDIO_TTL_SECONDS = 600
AUDIO_CACHE_MAX_ENTRIES = 256
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
ELEVENLABS_TIMEOUT_SECONDS = 8.0
DEFAULT_ELEVENLABS_MODEL_ID = "eleven_flash_v2_5"
_REDIS_NAMESPACE = "voice_tts"
_AUDIO_KEY = re.compile(r"^[0-9a-f]{64}$")
_VOICE_ID = re.compile(r"^[A-Za-z0-9]{8,64}$")


class SpeechUnavailable(Exception):
    """A provider cannot produce speech for this turn; the caller falls back to Twilio."""


def _now() -> float:
    return time.monotonic()


class _AudioCache:
    """Process-local TTL cache with a size bound. Expired entries are dropped on access."""

    def __init__(
        self,
        ttl_seconds: float,
        max_entries: int,
        clock: Callable[[], float] = lambda: _now(),
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._clock = clock
        self._entries: OrderedDict[str, tuple[float, bytes]] = OrderedDict()

    def get(self, key: str) -> Optional[bytes]:
        item = self._entries.get(key)
        if item is None:
            return None
        expires_at, data = item
        if self._clock() >= expires_at:
            self._entries.pop(key, None)
            return None
        return data

    def put(self, key: str, data: bytes) -> None:
        self._prune()
        self._entries[key] = (self._clock() + self._ttl, data)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()

    def _prune(self) -> None:
        now = self._clock()
        for key in [
            k for k, (expires_at, _) in self._entries.items() if now >= expires_at
        ]:
            del self._entries[key]


_local_cache = _AudioCache(AUDIO_TTL_SECONDS, AUDIO_CACHE_MAX_ENTRIES)
_TRANSPORT: Optional[httpx.AsyncBaseTransport] = None  # None: real network (production)


def _shared_backend() -> Any:
    """The Redis-backed cache when ``REDIS_URL`` is set; ``None`` means use the local cache."""
    if not os.getenv("REDIS_URL", "").strip():
        return None
    from app.services.cache import get_shared_cache

    backend = get_shared_cache(_REDIS_NAMESPACE)
    return backend if backend.name == "redis" else None


def _cache_store(key: str, audio: bytes) -> None:
    backend = _shared_backend()
    if backend is None:
        _local_cache.put(key, audio)
        return
    # Redis expires the key itself; audio is stored as base64 because the backend is JSON.
    backend.set(
        key, base64.b64encode(audio).decode("ascii"), ttl_seconds=AUDIO_TTL_SECONDS
    )


def _cache_load(key: str) -> Optional[bytes]:
    backend = _shared_backend()
    if backend is None:
        return _local_cache.get(key)
    raw = backend.get(key)
    return base64.b64decode(raw) if raw else None


def get_audio(key: str) -> Optional[bytes]:
    """Return cached MP3 bytes for ``key``, or ``None`` when unknown, expired or malformed."""
    if not _AUDIO_KEY.match(key or ""):
        return None
    try:
        return _cache_load(key)
    except Exception as e:  # noqa: BLE001
        # Exception type only: backend errors can embed connection details.
        log.warning("voice audio cache read failed (%s)", type(e).__name__)
        return None


class SpeechProvider(ABC):
    """Turns text into one TwiML speech verb (``<Say>`` or ``<Play>``)."""

    name: str = "speech"

    @abstractmethod
    async def speak(self, text: str) -> str: ...


class TwilioSayProvider(SpeechProvider):
    """Twilio's built-in voice via ``<Say>``. Always available."""

    name = "twilio"

    def __init__(self, voice: str) -> None:
        self._voice = voice

    async def speak(self, text: str) -> str:
        return twiml.say_verb(text, self._voice)


class ElevenLabsProvider(SpeechProvider):
    """ElevenLabs text-to-speech, cached briefly and played back through ``<Play>``."""

    name = "elevenlabs"

    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str,
        model_id: str,
        public_base_url: str,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id
        self._public_base_url = public_base_url.rstrip("/")
        # Tests replace ``_TRANSPORT`` with a mock transport so no request leaves the process.
        self._transport = transport if transport is not None else _TRANSPORT

    def audio_key(self, text: str) -> str:
        """Unguessable cache key: HMAC over the voice id and text, keyed with the API key."""
        message = f"{self._voice_id}\x00{text}".encode("utf-8")
        return hmac.new(
            self._api_key.encode("utf-8"), message, hashlib.sha256
        ).hexdigest()

    async def speak(self, text: str) -> str:
        if not self._public_base_url:
            log.warning(
                "PUBLIC_API_BASE_URL is not set; ElevenLabs audio cannot be played"
            )
            raise SpeechUnavailable("public API base URL is not configured")
        key = self.audio_key(text)
        if _cache_load(key) is None:
            audio = await self._synthesize(text)
            _cache_store(key, audio)
        return twiml.play_verb(f"{self._public_base_url}/api/voice/audio/{key}.mp3")

    async def _synthesize(self, text: str) -> bytes:
        url = ELEVENLABS_TTS_URL.format(voice_id=self._voice_id)
        headers = {"xi-api-key": self._api_key, "accept": "audio/mpeg"}
        body = {"text": text, "model_id": self._model_id}
        try:
            async with httpx.AsyncClient(
                timeout=ELEVENLABS_TIMEOUT_SECONDS, transport=self._transport
            ) as client:
                resp = await client.post(url, headers=headers, json=body)
        except Exception as e:  # noqa: BLE001
            # Exception type only: transport errors can embed the request URL and headers.
            log.warning(
                "ElevenLabs TTS request failed (%s); using Twilio voice",
                type(e).__name__,
            )
            raise SpeechUnavailable("request failed") from None
        if resp.status_code != 200 or not resp.content:
            # Status only: the response body is not logged.
            log.warning(
                "ElevenLabs TTS failed: HTTP %s; using Twilio voice", resp.status_code
            )
            raise SpeechUnavailable(f"HTTP {resp.status_code}")
        return resp.content


def select_provider(*, voice: str, cfg: Any) -> SpeechProvider:
    """ElevenLabs when both the key and a well-formed voice id are set; Twilio otherwise."""
    api_key = (getattr(cfg, "elevenlabs_api_key", "") or "").strip()
    voice_id = (getattr(cfg, "elevenlabs_voice_id", "") or "").strip()
    if api_key and voice_id:
        if not _VOICE_ID.match(voice_id):
            log.warning("ELEVENLABS_VOICE_ID is malformed; using Twilio voice")
            return TwilioSayProvider(voice)
        return ElevenLabsProvider(
            api_key=api_key,
            voice_id=voice_id,
            model_id=(
                getattr(cfg, "elevenlabs_model_id", "") or DEFAULT_ELEVENLABS_MODEL_ID
            ),
            public_base_url=getattr(cfg, "public_api_base_url", "") or "",
        )
    return TwilioSayProvider(voice)


async def render_speech(text: str, *, voice: str, cfg: Any) -> str:
    """Return the speech verb for one turn. Never raises: any failure becomes ``<Say>``."""
    provider = select_provider(voice=voice, cfg=cfg)
    if isinstance(provider, TwilioSayProvider):
        return await provider.speak(text)
    try:
        return await provider.speak(text)
    except SpeechUnavailable:
        pass  # already logged by the provider
    except Exception as e:  # noqa: BLE001
        log.warning(
            "ElevenLabs speech failed (%s); using Twilio voice", type(e).__name__
        )
    return await TwilioSayProvider(voice).speak(text)
