"""
T3 — Compressed vs Uncompressed Upload
========================================
Compares upload latency and throughput when the client pre-compresses
the payload with zstd (``Content-Encoding: zstd``) versus sending raw JSON.

Two Locust user classes run side-by-side so the comparison is captured
in a single test run.

Run example::

    locust -f scenarios/test_compressed_upload.py --headless \
           -u 50 -r 5 --run-time 5m \
           --csv=results/compressed_upload
"""

import io
import os
import sys

import zstandard as zstd
from locust import HttpUser, task, between, events

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers.config import Config
from helpers.auth import AuthHelper
from helpers.prov_generator import ProvGenerator

# Pre-generate raw and compressed payloads
_raw: dict[str, bytes] = {}
_compressed: dict[str, bytes] = {}


@events.test_start.add_listener
def _on_test_start(environment, **kwargs):
    compressor = zstd.ZstdCompressor(level=Config.ZSTD_LEVEL)
    for tier in Config.DOC_SIZES:
        raw = ProvGenerator.get(tier)
        _raw[tier] = raw
        _compressed[tier] = compressor.compress(raw)


class UncompressedUploadUser(HttpUser):
    """Baseline: uploads raw PROV-JSON without compression."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST
    weight = 1

    def on_start(self):
        self.auth = AuthHelper(self.host)

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

    def _upload(self, tier: str):
        payload = _raw[tier]
        files = {"document_file": (f"doc_{tier}.json", io.BytesIO(payload), "application/json")}
        with self.client.post(
            "/documents",
            files=files,
            headers=self.auth.headers,
            name=f"upload_uncompressed_{tier}",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class CompressedUploadUser(HttpUser):
    """Uploads zstd-pre-compressed payload with ``Content-Encoding: zstd``."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST
    weight = 1

    def on_start(self):
        self.auth = AuthHelper(self.host)

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

    def _upload(self, tier: str):
        payload = _compressed[tier]
        headers = {**self.auth.headers, "Content-Encoding": "zstd"}
        files = {"document_file": (f"doc_{tier}.json", io.BytesIO(payload), "application/json")}
        with self.client.post(
            "/documents",
            files=files,
            headers=headers,
            name=f"upload_compressed_{tier}",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
