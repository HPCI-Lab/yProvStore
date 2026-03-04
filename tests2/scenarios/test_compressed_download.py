"""
T4 — Compressed vs Uncompressed Download
==========================================
Compares download latency when the client sends ``Accept-Encoding: zstd``
(receiving compressed data and decompressing locally) versus plain download.

A seed phase uploads one document per size tier.  Two user classes then
download the *same* documents — one compressed, one not.

Run example::

    locust -f scenarios/test_compressed_download.py --headless \
           -u 50 -r 5 --run-time 5m \
           --csv=results/compressed_download
"""

import io
import os
import sys
import random
import threading
import time

import zstandard as zstd
from locust import HttpUser, task, between, events

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers.config import Config
from helpers.auth import AuthHelper
from helpers.prov_generator import ProvGenerator

# Shared PID pool
_pids: dict[str, list[str]] = {tier: [] for tier in Config.DOC_SIZES}
_seed_lock = threading.Lock()
_seeded = False

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def _seed_documents(host: str, auth: AuthHelper, count_per_tier: int = 3):
    global _seeded
    if _seeded:
        return
    with _seed_lock:
        if _seeded:
            return
        import requests as req

        for tier in Config.DOC_SIZES:
            payload = ProvGenerator.get(tier)
            for _ in range(count_per_tier):
                files = {"document_file": (f"seed_{tier}.json", io.BytesIO(payload), "application/json")}
                r = req.post(
                    f"{host}/documents",
                    files=files,
                    headers=auth.headers,
                    timeout=Config.REQUEST_TIMEOUT,
                )
                if r.status_code in (200, 201):
                    pid = r.json().get("document_record", {}).get("pid") or r.json().get("pid")
                    if pid:
                        _pids[tier].append(pid)
        _seeded = True


class UncompressedDownloadUser(HttpUser):
    """Baseline: downloads without requesting compression."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST
    weight = 1

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed_documents(self.host, self.auth)

    @task(4)
    def download_small(self):
        self._download("small")

    @task(3)
    def download_medium(self):
        self._download("medium")

    @task(2)
    def download_large(self):
        self._download("large")

    @task(1)
    def download_xlarge(self):
        self._download("xlarge")

    def _download(self, tier: str):
        pids = _pids.get(tier, [])
        if not pids:
            return
        pid = random.choice(pids)
        with self.client.get(
            f"/documents/{pid}",
            params={"stream": "true"},
            name=f"download_uncompressed_{tier}",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                _ = resp.content
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class CompressedDownloadUser(HttpUser):
    """Downloads with ``Accept-Encoding: zstd``, then decompresses locally.

    The total measured time includes the decompression step, giving a
    realistic end-to-end comparison.
    """

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST
    weight = 1

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed_documents(self.host, self.auth)
        self._decompressor = zstd.ZstdDecompressor()

    @task(4)
    def download_small(self):
        self._download("small")

    @task(3)
    def download_medium(self):
        self._download("medium")

    @task(2)
    def download_large(self):
        self._download("large")

    @task(1)
    def download_xlarge(self):
        self._download("xlarge")

    def _download(self, tier: str):
        pids = _pids.get(tier, [])
        if not pids:
            return
        pid = random.choice(pids)
        headers = {"Accept-Encoding": "zstd"}
        with self.client.get(
            f"/documents/{pid}",
            params={"stream": "true"},
            headers=headers,
            name=f"download_compressed_{tier}",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                raw = resp.content
                # Decompress if server returned zstd
                if raw[:4] == ZSTD_MAGIC:
                    _ = self._decompressor.decompress(raw)
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
