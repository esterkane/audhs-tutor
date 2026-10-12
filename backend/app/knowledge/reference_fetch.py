"""Bounded HTTPS for fixed public references; no redirects, proxies, credentials or assets."""

import asyncio
import http.client
import ipaddress
import socket
import ssl
import threading
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.core.errors import AppError

MAX_BYTES = 2_000_000
MAX_SECONDS = 20


@dataclass(frozen=True)
class FetchedPage:
    raw: bytes
    content_type: str


def public_addresses(host: str) -> list[str]:
    values = list(
        dict.fromkeys(
            str(row[4][0]) for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        )
    )
    if not values or any(
        not ipaddress.ip_address(value).is_global
        or ipaddress.ip_address(value).is_multicast
        or ipaddress.ip_address(value).is_reserved
        for value in values
    ):
        raise AppError(
            "reference_address_blocked", "Reference resolved to a non-public network address.", 422
        )
    return values


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, timeout: float):
        self.tls_context = ssl.create_default_context()
        super().__init__(host, timeout=timeout, context=self.tls_context)
        self.address = address

    def connect(self) -> None:
        # Connect only to the validated address; certificate/SNI still use the original host.
        raw = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self.tls_context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def fetch_sync(url: str, cancelled: threading.Event) -> FetchedPage:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        raise AppError(
            "reference_url_blocked", "Only fixed HTTPS documentation pages are supported.", 422
        )
    deadline = time.monotonic() + MAX_SECONDS
    addresses = public_addresses(parsed.hostname)
    remaining = deadline - time.monotonic()
    if cancelled.is_set() or remaining <= 0:
        raise TimeoutError("Reference download timed out")
    conn = _PinnedHTTPS(parsed.hostname, addresses[0], min(remaining, 8))
    try:
        conn.request(
            "GET",
            parsed.path or "/",
            headers={
                "User-Agent": "AuDHS-Tutor/local-reference-copy",
                "Accept": "text/html",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
        response = conn.getresponse()
        if response.status != 200:
            raise AppError(
                "reference_unavailable",
                f"Reference returned HTTP {response.status}; redirects are not followed.",
                502,
            )
        content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise AppError("reference_format", "Reference did not return an HTML document.", 422)
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise AppError(
                "reference_encoding", "Compressed reference responses are not accepted.", 422
            )
        length = response.getheader("Content-Length")
        if length is not None and (not length.isdigit() or int(length) > MAX_BYTES):
            raise AppError("reference_too_large", "Reference exceeds the download size limit.", 422)
        parts: list[bytes] = []
        total = 0
        while True:
            remaining = deadline - time.monotonic()
            if cancelled.is_set() or remaining <= 0:
                raise TimeoutError("Reference download timed out")
            if conn.sock is not None:
                conn.sock.settimeout(min(remaining, 8))
            part = response.read1(min(65536, MAX_BYTES + 1 - total))
            if not part:
                break
            parts.append(part)
            total += len(part)
            if total > MAX_BYTES:
                raise AppError(
                    "reference_too_large", "Reference exceeds the download size limit.", 422
                )
        if length is not None and total != int(length):
            raise AppError(
                "reference_incomplete", "Reference download was incomplete; no copy saved.", 502
            )
        return FetchedPage(b"".join(parts), content_type)
    finally:
        conn.close()


async def fetch(url: str) -> FetchedPage:
    cancelled = threading.Event()
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(fetch_sync, url, cancelled), MAX_SECONDS + 1
        )
    except AppError:
        raise
    except (OSError, TimeoutError, http.client.HTTPException, ValueError) as exc:
        raise AppError(
            "reference_download_failed",
            "Could not download this reference. Your existing local copy is unchanged.",
            502,
        ) from exc
    finally:
        cancelled.set()
