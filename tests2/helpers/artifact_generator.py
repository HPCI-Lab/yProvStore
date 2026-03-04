"""
Generate binary artifacts at configurable sizes for performance tests.

Artifacts in yProvStore are stored without compression, so random bytes are
appropriate (they represent opaque binary files such as images, HDF5, etc.).
"""

from __future__ import annotations

import os
import logging

from .config import Config

logger = logging.getLogger(__name__)

_cache: dict[str, bytes] = {}


def generate_artifact(size_bytes: int) -> tuple[str, bytes]:
    """Return ``(filename, data)`` for a random binary artifact."""
    data = os.urandom(size_bytes)
    filename = f"artifact_{size_bytes}.bin"
    return filename, data


def get_cached_artifact(tier: str) -> tuple[str, bytes]:
    """Return a cached artifact for the given size tier."""
    if tier not in _cache:
        target = Config.ARTIFACT_SIZES.get(tier)
        if target is None:
            raise ValueError(f"Unknown artifact tier: {tier!r}. Available: {list(Config.ARTIFACT_SIZES)}")
        logger.info("Generating binary artifact for tier '%s' (~%d bytes) …", tier, target)
        _cache[tier] = os.urandom(target)
        logger.info("Generated '%s' artifact: %d bytes.", tier, len(_cache[tier]))
    filename = f"artifact_{tier}.bin"
    return filename, _cache[tier]


class ArtifactGenerator:
    """Convenience facade used by test scenarios."""

    @staticmethod
    def get(tier: str) -> tuple[str, bytes]:
        return get_cached_artifact(tier)

    @staticmethod
    def get_all() -> dict[str, tuple[str, bytes]]:
        return {tier: get_cached_artifact(tier) for tier in Config.ARTIFACT_SIZES}
