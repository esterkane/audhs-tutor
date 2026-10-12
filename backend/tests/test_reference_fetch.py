import socket
import threading

import pytest

from app.core.errors import AppError
from app.knowledge import reference_fetch as fetch


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1", "::ffff:127.0.0.1", "224.0.0.1"],
)
def test_excludes_non_public_destinations(monkeypatch, address):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (address, 443))],
    )
    with pytest.raises(AppError, match="non-public"):
        fetch.public_addresses("docs.python.org")


def test_mixed_dns_answer_is_rejected(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 0, "", (ip, 443)) for ip in ["1.1.1.1", "127.0.0.1"]],
    )
    with pytest.raises(AppError):
        fetch.public_addresses("docs.python.org")


def test_tls_connect_uses_pinned_ip_and_original_hostname(monkeypatch):
    connected = []
    raw = object()
    monkeypatch.setattr(
        socket, "create_connection", lambda address, timeout: connected.append(address) or raw
    )
    conn = fetch._PinnedHTTPS("docs.python.org", "1.1.1.1", 1)

    class Context:
        def wrap_socket(self, sock, *, server_hostname):
            assert sock is raw
            assert server_hostname == "docs.python.org"
            return None

    conn.tls_context = Context()
    conn.connect()
    assert connected == [("1.1.1.1", 443)]


class Response:
    status = 200

    def __init__(self, body=b"<html>Example</html>", headers=None):
        self.body = body
        self.headers = headers or {"Content-Type": "text/html"}

    def getheader(self, key, default=None):
        return self.headers.get(key, default)

    def read1(self, count):
        part, self.body = self.body[:count], self.body[count:]
        return part


def wire(monkeypatch, response):
    requests = []
    monkeypatch.setattr(fetch, "public_addresses", lambda host: ["1.1.1.1"])

    class Connection:
        sock = None

        def __init__(self, host, address, timeout):
            assert address == "1.1.1.1"

        def request(self, method, path, headers):
            requests.append((method, path, headers))

        def getresponse(self):
            return response

        def close(self):
            pass

    monkeypatch.setattr(fetch, "_PinnedHTTPS", Connection)
    return requests


def test_plain_bounded_request_has_no_private_query_credentials_or_proxy(monkeypatch):
    calls = wire(monkeypatch, Response())
    assert fetch.fetch_sync(
        "https://docs.python.org/3/tutorial/", threading.Event()
    ).raw.startswith(b"<html>")
    assert calls[0][1] == "/3/tutorial/"
    assert set(calls[0][2]) == {"User-Agent", "Accept", "Accept-Encoding", "Connection"}


@pytest.mark.parametrize(
    "kind", ["redirect", "large", "declared_large", "binary", "compressed", "incomplete"]
)
def test_unsafe_responses_not_returned(monkeypatch, kind):
    response = Response()
    if kind == "redirect":
        response.status = 302
    if kind == "large":
        response.body = b"x" * (fetch.MAX_BYTES + 1)
    if kind == "declared_large":
        response.headers["Content-Length"] = str(fetch.MAX_BYTES + 1)
    if kind == "binary":
        response.headers["Content-Type"] = "application/octet-stream"
    if kind == "compressed":
        response.headers["Content-Encoding"] = "gzip"
    if kind == "incomplete":
        response.headers["Content-Length"] = "100"
    wire(monkeypatch, response)
    with pytest.raises(AppError):
        fetch.fetch_sync("https://docs.python.org/3/tutorial/", threading.Event())


def test_cancelled_dns_result_cannot_start_connection(monkeypatch):
    event = threading.Event()

    def resolved(host):
        event.set()
        return ["1.1.1.1"]

    monkeypatch.setattr(fetch, "public_addresses", resolved)
    monkeypatch.setattr(fetch, "_PinnedHTTPS", lambda *a: pytest.fail("Must not connect"))
    with pytest.raises(TimeoutError):
        fetch.fetch_sync("https://docs.python.org/3/tutorial/", event)
