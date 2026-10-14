"""Upload validation: extension allowlist and content-signature checks."""

import pytest

from app.api.branding.routes import _ASSET_HEADERS, _matches_signature
from app.services.document_processing import validate_upload


@pytest.mark.parametrize(
    ("name", "body"),
    [
        ("notes.txt", b"plain text"),
        ("readme.md", b"# Title"),
        ("data.csv", b"a,b\n1,2"),
        ("doc.pdf", b"%PDF-1.7\n..."),
        ("doc.docx", b"PK\x03\x04rest"),
        ("page.html", b"<html></html>"),
    ],
)
def test_supported_uploads_pass(name, body):
    validate_upload(name, body)


@pytest.mark.parametrize(
    ("name", "body"),
    [
        ("payload.exe", b"MZ\x90\x00"),
        ("script.sh", b"#!/bin/sh"),
        ("noext", b"hello"),
        ("fake.pdf", b"MZ\x90\x00not a pdf"),
        ("fake.docx", b"%PDF-1.4"),
        ("binary.txt", b"MZ\x90\x00\x00\x00"),
        ("nul.csv", b"a,b\x00c"),
    ],
)
def test_unsupported_or_spoofed_uploads_rejected(name, body):
    with pytest.raises(ValueError):
        validate_upload(name, body)


def test_brand_asset_signatures():
    assert _matches_signature("png", b"\x89PNG\r\n\x1a\nxxxx")
    assert not _matches_signature("png", b"<svg onload=alert(1)>")
    assert _matches_signature("webp", b"RIFF\x00\x00\x00\x00WEBPVP8 ")
    assert _matches_signature("svg", b"<?xml version='1.0'?><svg></svg>")
    assert not _matches_signature("svg", b"<html><script>alert(1)</script>")


def test_brand_assets_are_sandboxed():
    assert "sandbox" in _ASSET_HEADERS["Content-Security-Policy"]
    assert _ASSET_HEADERS["X-Content-Type-Options"] == "nosniff"
