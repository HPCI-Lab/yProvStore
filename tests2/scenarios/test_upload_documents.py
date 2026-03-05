"""
T1 — Document Upload Throughput
================================
Measures upload throughput (requests/sec, latency percentiles) for
**uncompressed** document uploads at each size tier.

Each Locust user authenticates on start-up, then continuously uploads
valid PROV-JSON documents as multipart ``document_file`` POSTs.

Run example::

    locust -f scenarios/test_upload_documents.py --headless \
           -u 50 -r 5 --run-time 5m \
           --csv=results/upload_docs
"""

import io
import os
import sys
import random

from locust import HttpUser, task, between, events

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers.config import Config
from helpers.auth import AuthHelper
from helpers.prov_generator import ProvGenerator


# Pre-generate payloads at import time (once per worker process)
_payloads: dict[str, bytes] = {}


@events.test_start.add_listener
def _on_test_start(environment, **kwargs):
    """Generate documents before any user spawns."""
    for tier in Config.DOC_SIZES:
        _payloads[tier] = ProvGenerator.get(tier)


class DocumentUploadUser(HttpUser):
    """Uploads PROV-JSON documents (uncompressed) at varying sizes."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST

    def on_start(self):
        self.auth = AuthHelper(self.host)

    # Weighted tasks: small documents are more common than huge ones
    @task(4)
    def upload_small(self):
        self._upload("small")

    @task(3)
    def upload_medium(self):
        self._upload("medium")

    @task(2)
    def upload_large(self):
        self._upload("large")

    @task(1)
    def upload_xlarge(self):
        self._upload("xlarge")

    @task(1)
    def upload_xxl(self):
        self._upload("xxl")

    @task(1)
    def upload_xxxl(self):
        self._upload("xxxl")

    # ── internal ────────────────────────────────────────────────────────
    def _upload(self, tier: str):
        payload = _payloads[tier]
        files = {
            "document_file": (f"document_{tier}.json", io.BytesIO(payload), "application/json"),
        }
        with self.client.post(
            "/documents",
            files=files,
            headers=self.auth.headers,
            name=f"upload_{tier}",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}: {resp.text[:200]}")
