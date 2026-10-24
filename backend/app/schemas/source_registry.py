"""Offline metadata inputs; URL validation does not establish fetch safety or rights."""

import ipaddress
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SourceRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1, max_length=2048)
    document_version_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("url")
    @classmethod
    def public_url(cls, value: str) -> str:
        if any(ord(c) < 33 or ord(c) == 127 for c in value) or "\\" in value:
            raise ValueError("Invalid source URL")
        try:
            parts = urlsplit(value)
            host = (parts.hostname or "").encode("idna").decode("ascii").lower()
            port = parts.port
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Invalid source URL") from exc
        if parts.scheme not in {"http", "https"} or not host:
            raise ValueError("Use an absolute HTTP(S) URL")
        if (
            parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
        ):
            raise ValueError("Credentials, query parameters and fragments are not supported")
        if host.endswith((".", ".localhost", ".local", ".internal")) or "." not in host:
            raise ValueError("Use a public source hostname")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("IP addresses are not supported")
        for label in host.split("."):
            if (
                not label
                or len(label) > 63
                or label.startswith("-")
                or label.endswith("-")
                or any(not (c.isascii() and (c.isalnum() or c == "-")) for c in label)
            ):
                raise ValueError("Invalid source hostname")
        authority = host
        if port is not None and (parts.scheme, port) not in {("https", 443), ("http", 80)}:
            authority = f"{host}:{port}"
        return urlunsplit((parts.scheme, authority, parts.path or "/", "", ""))


class SourceCheckInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["manual_metadata", "http_metadata", "repository_revision"]
    checked_at: datetime
    outcome: Literal["unchanged", "changed", "failed", "unknown"]
    fingerprint: str | None = Field(default=None, min_length=1, max_length=256)
    error_code: (
        Literal["timeout", "rate_limited", "access_denied", "unavailable", "invalid_response"]
        | None
    ) = None

    @field_validator("checked_at")
    @classmethod
    def aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("checked_at needs an explicit timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def consistent_evidence(self) -> "SourceCheckInput":
        if self.outcome in {"changed", "unchanged"} and (not self.fingerprint or self.error_code):
            raise ValueError("Successful metadata checks require a fingerprint and no error")
        if self.outcome in {"failed", "unknown"} and self.fingerprint is not None:
            raise ValueError("Failed or unknown checks cannot establish a new fingerprint")
        if self.outcome != "failed" and self.error_code is not None:
            raise ValueError("Only failed checks have an error code")
        return self
