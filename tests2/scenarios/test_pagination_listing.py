"""
T10 — Pagination & Listing Performance
========================================
Measures listing endpoint performance with different page sizes,
deep pagination offsets, and filters, as total document count grows.

Seed: ensures hundreds of documents exist.  Tasks exercise various
listing patterns concurrently.

Run example::

    locust -f scenarios/test_pagination_listing.py --headless \
           -u 30 -r 5 --run-time 5m \
           --csv=results/pagination
"""

import io
import os
import sys
import random
import threading
from datetime import datetime, timedelta, timezone

import requests as req
from locust import HttpUser, task, between

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers.config import Config
from helpers.auth import AuthHelper
from helpers.prov_generator import ProvGenerator

_seed_lock = threading.Lock()
_seeded = False
_total_seeded = 0

# Target a large base of documents for pagination stress
SEED_TARGET = int(os.getenv("PAGINATION_SEED_COUNT", "200"))


def _seed_many_documents(host: str, auth: AuthHelper):
    global _seeded, _total_seeded
    if _seeded:
        return
    with _seed_lock:
        if _seeded:
            return

        payload = ProvGenerator.get("small")
        for i in range(SEED_TARGET):
            files = {"document_file": (f"page_seed_{i}.json", io.BytesIO(payload), "application/json")}
            r = req.post(
                f"{host}/documents",
                files=files,
                headers=auth.headers,
                timeout=Config.REQUEST_TIMEOUT,
            )
            if r.status_code in (200, 201):
                _total_seeded += 1
            if (i + 1) % 50 == 0:
                print(f"  Seeded {i + 1}/{SEED_TARGET} documents …")
        _seeded = True
        print(f"  Pagination seed complete: {_total_seeded} documents.")


class PaginationUser(HttpUser):
    """Exercises document and artifact listing endpoints."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed_many_documents(self.host, self.auth)

    @task(4)
    def list_page_small(self):
        """Default page_size=10, random page."""
        page = random.randint(0, 10)
        with self.client.get(
            "/documents", params={"page": page, "page_size": 10},
            name="list_docs_ps10", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(3)
    def list_page_large(self):
        """page_size=100."""
        with self.client.get(
            "/documents", params={"page": 0, "page_size": 100},
            name="list_docs_ps100", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(2)
    def list_deep_page(self):
        """Deep pagination offset (page 50, page_size 10)."""
        with self.client.get(
            "/documents", params={"page": 50, "page_size": 10},
            name="list_docs_deep", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(2)
    def list_filtered_by_date(self):
        """Filter by created_after (recent 1-hour window)."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        with self.client.get(
            "/documents", params={"page": 0, "page_size": 20, "created_after": cutoff},
            name="list_docs_filtered", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def list_artifacts(self):
        """List artifacts."""
        with self.client.get(
            "/artifacts", params={"page": 0, "page_size": 10},
            name="list_artifacts", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
