"""Pinned outbound destinations for user-supplied URLs (SSRF hardening).

Checking a hostname and then letting the HTTP client resolve it again leaves a
DNS-rebinding window: the second answer can be a private address. This module
resolves a host once, rejects the destination unless every address is public,
and returns a target whose URL names the validated IP literal. The original
hostname is kept in the Host header and in TLS SNI, so virtual hosting and
certificate verification behave as before.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

REASON_UNRESOLVABLE = "unresolvable"
REASON_NON_PUBLIC = "non_public"


class UnsafeDestinationError(ValueError):
    """The URL does not point at an allowed public http(s) destination."""

    def __init__(self, reason: str, message: str = "") -> None:
        super().__init__(message or reason)
        self.reason = reason


@dataclass(frozen=True)
class PinnedTarget:
    """A URL whose host has been replaced by a validated IP address."""

    url: str
    address: Optional[str] = None
    host_header: Optional[str] = None
    sni_hostname: Optional[str] = None

    def headers(self) -> dict[str, str]:
        return {"Host": self.host_header} if self.host_header else {}

    def extensions(self) -> dict[str, Any]:
        return {"sni_hostname": self.sni_hostname} if self.sni_hostname else {}


def is_public_address(raw: str) -> bool:
    """True only for globally routable unicast addresses."""
    try:
        ip = ipaddress.ip_address(raw.split("%", 1)[0])
    except ValueError:
        return False
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
        or not ip.is_global
    )


def resolve_public_addresses(host: str, port: int) -> list[str]:
    """Resolve ``host`` once and require every returned address to be public."""
    if not host:
        raise UnsafeDestinationError(REASON_UNRESOLVABLE, "host is required")
    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
        except (OSError, UnicodeError) as exc:
            raise UnsafeDestinationError(
                REASON_UNRESOLVABLE, "host could not be resolved"
            ) from exc
        addresses = []
        for info in infos:
            address = info[4][0]
            if address not in addresses:
                addresses.append(address)
    if not addresses:
        raise UnsafeDestinationError(REASON_UNRESOLVABLE, "host could not be resolved")
    if not all(is_public_address(address) for address in addresses):
        raise UnsafeDestinationError(
            REASON_NON_PUBLIC,
            "host resolves to a private, loopback, reserved, or link-local address",
        )
    return addresses


def resolve_public_target(url: str, *, allow_plain_local: bool = False) -> PinnedTarget:
    """Validate ``url`` and pin it to the single address that was validated.

    ``allow_plain_local`` is for development-only callers that deliberately
    reach a local receiver; the URL is then returned unchanged and unpinned.
    """
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if not host:
        raise UnsafeDestinationError("no_host", "URL has no host.")
    if allow_plain_local:
        return PinnedTarget(url=url)
    if scheme not in ("http", "https"):
        raise UnsafeDestinationError("scheme", "URL must use http or https.")
    port = parts.port or (443 if scheme == "https" else 80)
    addresses = resolve_public_addresses(host, port)
    address = addresses[0]
    pinned_host = f"[{address}]" if ":" in address else address
    netloc = f"{pinned_host}:{parts.port}" if parts.port else pinned_host
    pinned_url = urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))
    display_host = f"[{host}]" if ":" in host else host
    host_header = f"{display_host}:{parts.port}" if parts.port else display_host
    return PinnedTarget(
        url=pinned_url,
        address=address,
        host_header=host_header,
        sni_hostname=host if scheme == "https" else None,
    )


async def pinned_request(
    client: Any, method: str, target: PinnedTarget, **kwargs: Any
) -> Any:
    """Send one request to a pinned target through an httpx client.

    Caller headers and extensions are merged first so the Host header and SNI
    always come from the validated target.
    """
    headers = {**(kwargs.pop("headers", None) or {}), **target.headers()}
    extensions = {**(kwargs.pop("extensions", None) or {}), **target.extensions()}
    send = getattr(client, method.lower())
    return await send(target.url, headers=headers, extensions=extensions, **kwargs)
