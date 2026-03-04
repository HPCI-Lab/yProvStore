"""
T9 — Metadata Operations
==========================
Measures metadata read and write latency, isolating DB-bound performance
from I/O-bound file operations.

Seed phase uploads N documents with metadata (title, description, keywords,
author).  Tasks then read and update metadata.

Run example::

    locust -f scenarios/test_metadata_operations.py --headless \
           -u 30 -r 5 --run-time 5m \
           --csv=results/metadata_ops
"""

import io
import json
import os
import sys
import random
import threading

import requests as req
from locust import HttpUser, task, between

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers.config import Config
from helpers.auth import AuthHelper
from helpers.prov_generator import ProvGenerator

_pids: list[str] = []
_seed_lock = threading.Lock()
_seeded = False

SEED_COUNT = 30


def _seed_with_metadata(host: str, auth: AuthHelper):
    global _seeded
    if _seeded:
        return
    with _seed_lock:
        if _seeded:
            return

        payload = ProvGenerator.get("small")
        for i in range(SEED_COUNT):
            metadata = json.dumps({
                "title": f"Metadata Test Document {i}",
                "description": f"This is a test document generated for performance testing, iteration {i}.",
                "keywords": [f"keyword_{i}", "perftest", "metadata"],
                "author": f"testauthor_{i}@example.com",
            })
            files = {"document_file": ("seed.json", io.BytesIO(payload), "application/json")}
            r = req.post(
                f"{host}/documents",
                files=files,
                params={"document_metadata": metadata},
                headers=auth.headers,
                timeout=Config.REQUEST_TIMEOUT,
            )
            if r.status_code in (200, 201):
                pid = r.json().get("document_record", {}).get("pid") or r.json().get("pid")
                if pid:
                    _pids.append(pid)
        _seeded = True


class MetadataUser(HttpUser):
    """Reads and updates document metadata."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed_with_metadata(self.host, self.auth)

    @task(7)
    def read_metadata(self):
        if not _pids:
            return
        pid = random.choice(_pids)
        with self.client.get(
            f"/documents/{pid}/metadata",
            name="metadata_read",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(3)
    def update_metadata(self):
        if not _pids:
            return
        pid = random.choice(_pids)
        update = {
            "description": f"Updated description at iteration {random.randint(0, 100000)}",
            "keywords": ["updated", "perftest", f"kw_{random.randint(0, 100)}"],
        }
        with self.client.patch(
            f"/documents/{pid}/metadata",
            json=update,
            headers=self.auth.headers,
            name="metadata_update",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def get_schema(self):
        with self.client.get(
            "/metadata/schema",
            name="metadata_schema",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
