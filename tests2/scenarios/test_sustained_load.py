"""
T12 — Sustained Load / Endurance Test
=======================================
Detects memory leaks, connection pool exhaustion, or performance
degradation over time.

Runs a moderate number of users with a mixed read/write workload for
an extended period (30–60 minutes by default).

Run example::

    locust -f scenarios/test_sustained_load.py --headless \
           -u 25 -r 5 --run-time 30m \
           --csv=results/sustained
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


def _seed(host: str, auth: AuthHelper, count: int = 20):
    global _seeded
    if _seeded:
        return
    with _seed_lock:
        if _seeded:
            return
        import requests as req

        for _ in range(count):
            files = {"document_file": ("seed.json", io.BytesIO(_payload), "application/json")}
            r = req.post(f"{host}/documents", files=files, headers=auth.headers, timeout=Config.REQUEST_TIMEOUT)
            if r.status_code in (200, 201):
                pid = r.json().get("document_record", {}).get("pid") or r.json().get("pid")
                if pid:
                    _pids.append(pid)
        _seeded = True


class SustainedLoadUser(HttpUser):
    """Mixed workload for endurance testing.

    70 % reads, 20 % writes, 10 % listing/metadata — sustained for a
    prolonged period to surface degradation trends.
    """

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed(self.host, self.auth)

    @task(7)
    def download(self):
        if not _pids:
            return
        pid = random.choice(_pids)
        with self.client.get(
            f"/documents/{pid}", params={"stream": "true"},
            name="sustained_download", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                _ = resp.content
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(2)
    def upload(self):
        files = {"document_file": ("doc.json", io.BytesIO(_payload), "application/json")}
        with self.client.post(
            "/documents", files=files, headers=self.auth.headers,
            name="sustained_upload", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                pid = resp.json().get("document_record", {}).get("pid") or resp.json().get("pid")
                if pid:
                    _pids.append(pid)
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def list_and_metadata(self):
        # Alternate between listing and metadata read
        if random.random() < 0.5:
            with self.client.get(
                "/documents", params={"page": random.randint(0, 5), "page_size": 10},
                name="sustained_list", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
            ) as resp:
                if resp.status_code == 200:
                    resp.success()
                else:
                    resp.failure(f"HTTP {resp.status_code}")
        else:
            if not _pids:
                return
            pid = random.choice(_pids)
            with self.client.get(
                f"/documents/{pid}/metadata",
                name="sustained_metadata", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
            ) as resp:
                if resp.status_code == 200:
                    resp.success()
                else:
                    resp.failure(f"HTTP {resp.status_code}")
