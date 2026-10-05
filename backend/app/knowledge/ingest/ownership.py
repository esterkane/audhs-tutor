"""Compatibility surface: existing import locks keep their original namespace and identity."""

from app.core.local_ownership import LocalOwnership as RunOwnership
from app.core.local_ownership import OwnershipUnavailable as OwnershipUnavailable

__all__ = ["RunOwnership", "OwnershipUnavailable"]
