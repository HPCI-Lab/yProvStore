"""
T14 — Maximum Throughput / Breaking Point
==========================================
Discovers the maximum sustained RPS the application can handle before
errors begin or latency degrades beyond acceptable thresholds.

Uses a simple mixed workload (upload + download) with **zero wait time**
between requests so each Locust user fires as fast as possible.

Intended to be run via ``run_max_throughput_sweep.py`` which ramps through
progressively higher user counts, collecting RPS / error-rate / latency
at each step.

Can also be run standalone at a single user count::

    locust -f scenarios/test_max_throughput.py --headless \\
           -u 100 -r 20 --run-time 2m \\
           --csv=results/max_rps_100
"""

import io
import os
import sys
import random
import threading

from locust import HttpUser, task, between, constant, events

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers.config import Config
from helpers.auth import AuthHelper
from helpers.prov_generator import ProvGenerator

# Pre-generate payloads
_payloads: dict[str, bytes] = {}

# Shared PID pool for downloads
_pids: list[str] = []
_pid_lock = threading.Lock()


@events.test_start.add_listener
def _on_test_start(environment, **kwargs):
    """Generate payloads — use only small & medium to keep focus on throughput."""
    for tier in ("small", "medium"):
        _payloads[tier] = ProvGenerator.get(tier)


class MaxThroughputUser(HttpUser):
    """Fires requests as fast as possible (zero wait) to find the ceiling."""

    # No wait — maximum pressure
    wait_time = constant(0)
    host = Config.TARGET_HOST

    def on_start(self):
        self.auth = AuthHelper(self.host)
        # Seed a few documents so downloads have targets
        self._seed(count=3)

    def _seed(self, count: int = 3):
        """Upload a handful of small docs so download tasks work."""
        for _ in range(count):
            payload = _payloads["small"]
            files = {
                "document_file": ("seed.json", io.BytesIO(payload), "application/json"),
            }
            try:
                r = self.client.post(
                    "/documents",
                    files=files,
                    headers=self.auth.headers,
                    timeout=Config.REQUEST_TIMEOUT,
                    name="seed",
                )
                if r.status_code in (200, 201):
                    pid = r.json().get("document_record", {}).get("pid") or r.json().get("pid")
                    if pid:
                        with _pid_lock:
                            _pids.append(pid)
            except Exception:
                pass

    @task(5)
    def upload_small(self):
        payload = _payloads["small"]
        files = {
            "document_file": ("rps_small.json", io.BytesIO(payload), "application/json"),
        }
        with self.client.post(
            "/documents",
            files=files,
            headers=self.auth.headers,
            name="upload_small",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                pid = resp.json().get("document_record", {}).get("pid") or resp.json().get("pid")
                if pid:
                    with _pid_lock:
                        _pids.append(pid)
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(3)
    def upload_medium(self):
        payload = _payloads["medium"]
        files = {
            "document_file": ("rps_medium.json", io.BytesIO(payload), "application/json"),
        }
        with self.client.post(
            "/documents",
            files=files,
            headers=self.auth.headers,
            name="upload_medium",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(5)
    def download_document(self):
        with _pid_lock:
            if not _pids:
                return
            pid = random.choice(_pids)
        with self.client.get(
            f"/documents/{pid}",
            params={"stream": "true"},
            headers=self.auth.headers,
            name="download",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                _ = resp.content
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(2)
    def list_documents(self):
        with self.client.get(
            "/documents",
            params={"page": 1, "page_size": 20},
            headers=self.auth.headers,
            name="list",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
