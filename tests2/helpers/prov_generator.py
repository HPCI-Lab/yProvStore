"""
Generate valid PROV-JSON documents at configurable sizes.

Documents follow the W3C PROV-JSON structure used by yProvStore, with
activities, entities, ``used`` and ``wasGeneratedBy`` relations.
One document per size tier is pre-generated at import time and cached so
Locust workers don't waste CPU re-building payloads on every request.
"""

from __future__ import annotations

import json
import uuid
import logging
from typing import Any

from .config import Config

logger = logging.getLogger(__name__)


def _make_activity(idx: int) -> tuple[str, dict[str, Any]]:
    aid = f"activity_{idx}_{uuid.uuid4().hex[:8]}"
    return aid, {
        "prov:startTime": "2025-01-01T00:00:00Z",
        "prov:endTime": "2025-01-01T00:05:00Z",
        "prov:label": f"activity_{idx}",
        "prov:type": "prov:Activity",
    }


def _make_entity(idx: int) -> tuple[str, dict[str, Any]]:
    eid = f"entity_{idx}_{uuid.uuid4().hex[:8]}"
    return eid, {
        "prov:location": f"https://example.org/entity/{idx}",
        "prov:label": f"entity_{idx}",
        "prov:type": "prov:Entity",
    }


def generate_prov_document(target_bytes: int) -> dict[str, Any]:
    """Build a valid PROV-JSON dict targeting approximately *target_bytes*.

    The strategy: keep adding activities + entities + relations until the
    JSON-serialised size is within ~10 % of the target.  For very small
    targets (< 200 bytes) we return a minimal document.
    """
    doc: dict[str, Any] = {
        "prefix": {
            "default": "http://example.org/",
        },
        "activity": {},
        "entity": {},
        "used": {},
        "wasGeneratedBy": {},
    }

    batch = max(1, target_bytes // 500)  # rough estimate: ~500 bytes per activity+entity+2 relations
    idx = 0

    while True:
        current_size = len(json.dumps(doc, separators=(",", ":")))
        if current_size >= target_bytes * 0.95:
            break

        # Add a batch of elements
        for _ in range(batch):
            aid, aval = _make_activity(idx)
            eid_in, eval_in = _make_entity(idx * 2)
            eid_out, eval_out = _make_entity(idx * 2 + 1)

            doc["activity"][aid] = aval
            doc["entity"][eid_in] = eval_in
            doc["entity"][eid_out] = eval_out

            used_id = f"_:used_{idx}_{uuid.uuid4().hex[:6]}"
            doc["used"][used_id] = {
                "prov:entity": eid_in,
                "prov:activity": aid,
            }

            gen_id = f"_:gen_{idx}_{uuid.uuid4().hex[:6]}"
            doc["wasGeneratedBy"][gen_id] = {
                "prov:entity": eid_out,
                "prov:activity": aid,
            }
            idx += 1

        # Reduce batch size as we approach the target to avoid massive overshoot
        remaining = target_bytes - len(json.dumps(doc, separators=(",", ":")))
        batch = max(1, remaining // 500)

    return doc


def generate_prov_bytes(target_bytes: int) -> bytes:
    """Return JSON-encoded bytes of a generated PROV document."""
    doc = generate_prov_document(target_bytes)
    return json.dumps(doc).encode("utf-8")


# ── Pre-generated document cache ────────────────────────────────────────────
_cache: dict[str, bytes] = {}


def get_cached_document(tier: str) -> bytes:
    """Return pre-generated PROV-JSON bytes for a size tier.

    Tiers: ``small``, ``medium``, ``large``, ``xlarge`` (from ``Config.DOC_SIZES``).
    """
    if tier not in _cache:
        target = Config.DOC_SIZES.get(tier)
        if target is None:
            raise ValueError(f"Unknown document tier: {tier!r}. Available: {list(Config.DOC_SIZES)}")
        logger.info("Generating PROV-JSON document for tier '%s' (~%d bytes) …", tier, target)
        _cache[tier] = generate_prov_bytes(target)
        logger.info("Generated '%s' document: %d bytes actual.", tier, len(_cache[tier]))
    return _cache[tier]


class ProvGenerator:
    """Convenience facade used by test scenarios."""

    @staticmethod
    def get(tier: str) -> bytes:
        return get_cached_document(tier)

    @staticmethod
    def get_all() -> dict[str, bytes]:
        return {tier: get_cached_document(tier) for tier in Config.DOC_SIZES}
