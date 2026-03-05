"""
T2 — Document Download Throughput
==================================
Measures download throughput across document size tiers.

A seed phase (``on_start``) uploads one document per size tier and stores
each PID.  Tasks then repeatedly download those documents via streaming GET.

Run example::

    locust -f scenarios/test_download_documents.py --headless \
           -u 50 -r 5 --run-time 5m \
           --csv=results/download_docs
"""

import io
import os
import sys
import random
import threading

from locust import HttpUser, task, between, events

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers.config import Config
from helpers.auth import AuthHelper
from helpers.prov_generator import ProvGenerator


# Shared PID pool: tier -> list[str]
_pids: dict[str, list[str]] = {tier: [] for tier in Config.DOC_SIZES}
_seed_lock = threading.Lock()
_seeded = False


def _seed_documents(host: str, auth: AuthHelper, count_per_tier: int = 3):
    """Upload a few documents per tier so download tasks have targets."""
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
                files = {
                    "document_file": (f"seed_{tier}.json", io.BytesIO(payload), "application/json"),
                }
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


class DocumentDownloadUser(HttpUser):
    """Downloads previously-seeded documents at varying sizes."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST

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

    @task(1)
    def download_xxl(self):
        self._download("xxl")

    @task(1)
    def download_xxxl(self):
        self._download("xxxl")

    def _download(self, tier: str):
        pids = _pids.get(tier, [])
        if not pids:
            return  # no seed docs available
        pid = random.choice(pids)
        with self.client.get(
            f"/documents/{pid}",
            params={"stream": "true"},
            name=f"download_{tier}",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                # consume the full body so timing is accurate
                _ = resp.content
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}: {resp.text[:200]}")
