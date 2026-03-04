"""
T7 — Scalability / Concurrent Users
=====================================
Shows how throughput and latency degrade as concurrent users increase.

A *single* user class performs a mixed 70 % read / 30 % write workload on
**medium**-sized documents.  Run this file multiple times with increasing
``-u`` values (1, 5, 10, 25, 50, 100, 200) and merge the CSVs afterwards —
or use the companion wrapper ``run_scalability_sweep.py``.

Run example (single point)::

    locust -f scenarios/test_scalability.py --headless \
           -u 25 -r 5 --run-time 3m \
           --csv=results/scalability_25

Run the full sweep::

    python scenarios/run_scalability_sweep.py
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

_payload: bytes = b""
_pids: list[str] = []
_seed_lock = threading.Lock()
_seeded = False

TIER = "medium"


@events.test_start.add_listener
def _on_test_start(environment, **kwargs):
    global _payload
    _payload = ProvGenerator.get(TIER)


def _seed_documents(host: str, auth: AuthHelper, count: int = 10):
    global _seeded
    if _seeded:
        return
    with _seed_lock:
        if _seeded:
            return
        import requests as req

        for _ in range(count):
            files = {"document_file": ("seed.json", io.BytesIO(_payload), "application/json")}
            r = req.post(
                f"{host}/documents",
                files=files,
                headers=auth.headers,
                timeout=Config.REQUEST_TIMEOUT,
            )
            if r.status_code in (200, 201):
                pid = r.json().get("document_record", {}).get("pid") or r.json().get("pid")
                if pid:
                    _pids.append(pid)
        _seeded = True


class ScalabilityUser(HttpUser):
    """Mixed read/write user for scalability sweep."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed_documents(self.host, self.auth)

    @task(7)
    def download_document(self):
        if not _pids:
            return
        pid = random.choice(_pids)
        with self.client.get(
            f"/documents/{pid}",
            params={"stream": "true"},
            name="scalability_download",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                _ = resp.content
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(3)
    def upload_document(self):
        files = {"document_file": ("doc.json", io.BytesIO(_payload), "application/json")}
        with self.client.post(
            "/documents",
            files=files,
            headers=self.auth.headers,
            name="scalability_upload",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                pid = resp.json().get("document_record", {}).get("pid") or resp.json().get("pid")
                if pid:
                    _pids.append(pid)
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
