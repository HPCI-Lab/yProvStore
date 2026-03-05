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

# Shared pool for read-only operations (any user can read metadata)
_all_pids: list[str] = []
_all_pids_lock = threading.Lock()

SEED_COUNT_PER_USER = 10


class MetadataUser(HttpUser):
    """Reads and updates document metadata.

    Each Locust user seeds its own documents in ``on_start`` so it has
    WRITE permission on them.  Read tasks draw from the global pool
    (metadata reads are public); write tasks only target own documents.
    """

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST

    def on_start(self):
        self.auth = AuthHelper(self.host)
        self._own_pids: list[str] = []
        self._seed_own_documents()

    def _seed_own_documents(self):
        """Upload documents owned by *this* user so PATCH is allowed."""
        payload = ProvGenerator.get("small")
        for i in range(SEED_COUNT_PER_USER):
            metadata = json.dumps({
                "title": f"Metadata Test Document {i}",
                "description": f"Test document for performance testing, iteration {i}.",
                "keywords": [f"keyword_{i}", "perftest", "metadata"],
                "author": self.auth.email,
            })
            files = {"document_file": ("seed.json", io.BytesIO(payload), "application/json")}
            r = req.post(
                f"{self.host}/documents",
                files=files,
                params={"document_metadata": metadata},
                headers=self.auth.headers,
                timeout=Config.REQUEST_TIMEOUT,
            )
            if r.status_code in (200, 201):
                pid = r.json().get("document_record", {}).get("pid") or r.json().get("pid")
                if pid:
                    self._own_pids.append(pid)
                    with _all_pids_lock:
                        _all_pids.append(pid)

    @task(7)
    def read_metadata(self):
        # Reads are public — pick from global pool for variety
        with _all_pids_lock:
            pool = list(_all_pids) if _all_pids else list(self._own_pids)
        if not pool:
            return
        pid = random.choice(pool)
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
        # Writes require ownership — only use own PIDs
        if not self._own_pids:
            return
        pid = random.choice(self._own_pids)
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
