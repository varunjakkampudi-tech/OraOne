"""Voice speech provider: ElevenLabs selection, Twilio fallback, audio route, cache and log hygiene.

No network: ElevenLabs calls go through an httpx.MockTransport, and the audio route is
exercised with TestClient. The real ElevenLabs API is never called.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.voice import routes as voice_routes
from app.services.voice import tts

PUBLIC_BASE = "https://voice.example.test"
SECRET_KEY = "el-test-SECRET-key-0123456789"
VOICE_ID = "VoiceId123456"
SPOKEN = "Our hours are Tuesday evening, confidential phrase"
MP3 = b"ID3-fake-mp3-bytes"


def _cfg(**overrides):
    base = {
        "elevenlabs_api_key": "",
        "elevenlabs_voice_id": "",
        "elevenlabs_model_id": "",
        "public_api_base_url": PUBLIC_BASE,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _eleven_cfg(**overrides):
    base = {"elevenlabs_api_key": SECRET_KEY, "elevenlabs_voice_id": VOICE_ID}
    base.update(overrides)
    return _cfg(**base)


class _Mock:
    """Records requests and answers with a fixed status, body, or exception."""

    def __init__(self, status=200, content=MP3, error=None):
        self.status = status
        self.content = content
        self.error = error
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if self.error is not None:
                raise self.error
            return httpx.Response(self.status, content=self.content)

        return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    tts._local_cache.clear()
    monkeypatch.setattr(tts, "_TRANSPORT", None)
    yield
    tts._local_cache.clear()


def _use_mock(monkeypatch, mock: _Mock) -> None:
    monkeypatch.setattr(tts, "_TRANSPORT", mock.transport())


def _render(text: str, cfg) -> str:
    return asyncio.run(tts.render_speech(text, voice="alice", cfg=cfg))


# --- provider selection ------------------------------------------------------


def test_selects_twilio_when_no_elevenlabs_settings():
    provider = tts.select_provider(voice="alice", cfg=_cfg())
    assert isinstance(provider, tts.TwilioSayProvider)


@pytest.mark.parametrize(
    "overrides",
    [{"elevenlabs_api_key": SECRET_KEY}, {"elevenlabs_voice_id": VOICE_ID}],
)
def test_selects_twilio_when_only_one_elevenlabs_setting_is_present(overrides):
    provider = tts.select_provider(voice="alice", cfg=_cfg(**overrides))
    assert isinstance(provider, tts.TwilioSayProvider)


def test_selects_elevenlabs_when_key_and_voice_id_are_set():
    provider = tts.select_provider(voice="alice", cfg=_eleven_cfg())
    assert isinstance(provider, tts.ElevenLabsProvider)
    assert provider._model_id == tts.DEFAULT_ELEVENLABS_MODEL_ID


def test_model_id_can_be_overridden():
    provider = tts.select_provider(
        voice="alice", cfg=_eleven_cfg(elevenlabs_model_id="m-2")
    )
    assert provider._model_id == "m-2"


@pytest.mark.parametrize(
    "bad_voice_id", ["../../etc/passwd", "short", "has space in it!"]
)
def test_malformed_voice_id_falls_back_to_twilio(bad_voice_id):
    cfg = _eleven_cfg(elevenlabs_voice_id=bad_voice_id)
    assert isinstance(
        tts.select_provider(voice="alice", cfg=cfg), tts.TwilioSayProvider
    )


def test_twilio_provider_speaks_with_the_configured_voice():
    verb = _render(SPOKEN, _cfg())
    assert verb.startswith('<Say voice="alice">')
    assert "<Play" not in verb


# --- ElevenLabs success and cache -------------------------------------------


def test_elevenlabs_success_returns_play_url_and_caches_audio(monkeypatch):
    mock = _Mock()
    _use_mock(monkeypatch, mock)
    cfg = _eleven_cfg()

    verb = _render(SPOKEN, cfg)

    match = re.fullmatch(
        rf"<Play>{re.escape(PUBLIC_BASE)}/api/voice/audio/([0-9a-f]{{64}})\.mp3</Play>",
        verb,
    )
    assert match, verb
    key = match.group(1)
    assert tts.get_audio(key) == MP3

    request = mock.requests[0]
    assert request.url.path == f"/v1/text-to-speech/{VOICE_ID}"
    assert request.headers["xi-api-key"] == SECRET_KEY
    assert request.headers["accept"] == "audio/mpeg"
    body = request.read()
    assert b'"model_id":"eleven_flash_v2_5"' in body


def test_repeated_text_is_served_from_cache_without_a_second_request(monkeypatch):
    mock = _Mock()
    _use_mock(monkeypatch, mock)
    cfg = _eleven_cfg()

    first = _render(SPOKEN, cfg)
    second = _render(SPOKEN, cfg)

    assert first == second
    assert len(mock.requests) == 1


def test_audio_key_depends_on_voice_id_and_text_only():
    a = tts.ElevenLabsProvider(
        api_key="k", voice_id=VOICE_ID, model_id="m", public_base_url=PUBLIC_BASE
    )
    b = tts.ElevenLabsProvider(
        api_key="k", voice_id="OtherVoice99", model_id="m", public_base_url=PUBLIC_BASE
    )
    assert a.audio_key("hi") == a.audio_key("hi")
    assert a.audio_key("hi") != a.audio_key("hello")
    assert a.audio_key("hi") != b.audio_key("hi")
    assert re.fullmatch(r"[0-9a-f]{64}", a.audio_key("hi"))


# --- ElevenLabs failure falls back to Twilio for that turn -------------------


@pytest.mark.parametrize("status", [401, 429, 500])
def test_elevenlabs_http_error_falls_back_to_twilio_say(monkeypatch, caplog, status):
    _use_mock(monkeypatch, _Mock(status=status, content=b"{}"))
    caplog.set_level(logging.DEBUG)

    verb = _render(SPOKEN, _eleven_cfg())

    assert verb.startswith('<Say voice="alice">')
    assert f"HTTP {status}" in caplog.text


def test_elevenlabs_transport_error_falls_back_to_twilio_say(monkeypatch):
    _use_mock(monkeypatch, _Mock(error=httpx.ConnectError("boom")))
    assert _render(SPOKEN, _eleven_cfg()).startswith("<Say")


def test_elevenlabs_empty_body_falls_back_to_twilio_say(monkeypatch):
    _use_mock(monkeypatch, _Mock(status=200, content=b""))
    assert _render(SPOKEN, _eleven_cfg()).startswith("<Say")


def test_missing_public_base_url_falls_back_without_a_request(monkeypatch):
    mock = _Mock()
    _use_mock(monkeypatch, mock)
    verb = _render(SPOKEN, _eleven_cfg(public_api_base_url=""))
    assert verb.startswith("<Say")
    assert mock.requests == []


def test_unexpected_provider_error_falls_back_to_twilio_say(monkeypatch):
    async def explode(self, text):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(tts.ElevenLabsProvider, "speak", explode)
    assert _render(SPOKEN, _eleven_cfg()).startswith("<Say")


# --- audio route -------------------------------------------------------------


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(voice_routes.router)
    return TestClient(app)


def test_audio_route_returns_404_for_unknown_key(client):
    response = client.get("/api/voice/audio/" + "a" * 64 + ".mp3")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "bad", ["short.mp3", "A" * 64 + ".mp3", "g" * 64 + ".mp3", "%2e%2e.mp3"]
)
def test_audio_route_returns_404_for_malformed_keys(client, bad):
    assert client.get("/api/voice/audio/" + bad).status_code == 404


def test_audio_route_serves_audio_this_server_cached(client, monkeypatch):
    _use_mock(monkeypatch, _Mock())
    verb = _render(SPOKEN, _eleven_cfg())
    url = re.search(r"<Play>(.*)</Play>", verb).group(1)
    path = url[len(PUBLIC_BASE) :]

    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == MP3


def test_audio_route_404_after_ttl_expiry(client, monkeypatch):
    clock = {"now": 1000.0}
    monkeypatch.setattr(tts, "_now", lambda: clock["now"])
    _use_mock(monkeypatch, _Mock())
    verb = _render(SPOKEN, _eleven_cfg())
    path = re.search(r"<Play>(.*)</Play>", verb).group(1)[len(PUBLIC_BASE) :]

    clock["now"] += tts.AUDIO_TTL_SECONDS + 1

    assert client.get(path).status_code == 404


# --- cache TTL and bounds ----------------------------------------------------


def test_cache_entry_is_served_until_ttl_then_expires(monkeypatch):
    clock = {"now": 500.0}
    monkeypatch.setattr(tts, "_now", lambda: clock["now"])
    key = "b" * 64
    tts._local_cache.put(key, MP3)

    clock["now"] = 500.0 + tts.AUDIO_TTL_SECONDS - 1
    assert tts.get_audio(key) == MP3

    clock["now"] = 500.0 + tts.AUDIO_TTL_SECONDS
    assert tts.get_audio(key) is None


def test_cache_size_is_bounded_and_evicts_oldest():
    cache = tts._AudioCache(ttl_seconds=600, max_entries=3, clock=lambda: 0.0)
    for i in range(5):
        cache.put(str(i), b"x")
    assert len(cache._entries) == 3
    assert cache.get("0") is None
    assert cache.get("4") == b"x"


def test_expired_entries_are_pruned_on_write():
    now = {"t": 0.0}
    cache = tts._AudioCache(ttl_seconds=10, max_entries=100, clock=lambda: now["t"])
    cache.put("old", b"x")
    now["t"] = 20.0
    cache.put("new", b"y")
    assert "old" not in cache._entries


def test_shared_redis_backend_stores_base64_with_native_ttl(monkeypatch):
    class FakeRedisBackend:
        name = "redis"

        def __init__(self):
            self.store = {}
            self.ttls = {}

        def set(self, key, value, ttl_seconds=None):
            self.store[key] = value
            self.ttls[key] = ttl_seconds

        def get(self, key):
            return self.store.get(key)

    backend = FakeRedisBackend()
    monkeypatch.setenv("REDIS_URL", "redis://unused")
    monkeypatch.setattr(tts, "_shared_backend", lambda: backend)
    key = "c" * 64

    tts._cache_store(key, MP3)

    assert backend.ttls[key] == tts.AUDIO_TTL_SECONDS
    assert base64.b64decode(backend.store[key]) == MP3
    assert tts.get_audio(key) == MP3


# --- logging hygiene ---------------------------------------------------------


@pytest.mark.parametrize("status", [200, 500])
def test_no_key_or_spoken_text_is_logged(monkeypatch, caplog, status):
    _use_mock(monkeypatch, _Mock(status=status))
    caplog.set_level(logging.DEBUG)

    _render(SPOKEN, _eleven_cfg())
    _render("second turn text", _eleven_cfg(elevenlabs_voice_id="OtherVoice99"))

    logged = caplog.text + " ".join(r.getMessage() for r in caplog.records)
    assert SECRET_KEY not in logged
    assert "confidential phrase" not in logged
    assert "second turn text" not in logged
