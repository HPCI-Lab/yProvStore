"""
T6 — Artifact Download Throughput
==================================
Tests the full presigned-URL-based artifact download flow under load.

Seed phase uploads artifacts; tasks then:
1. GET ``/artifacts/{pid}/download/url`` → presigned download URL
2. GET proxy download URL with ``stream=true``

Run example::

    locust -f scenarios/test_download_artifacts.py --headless \
           -u 30 -r 5 --run-time 5m \
           --csv=results/download_artifacts
"""

import io
import os
import sys
import random
import threading

import requests as req
from locust import HttpUser, task, between, events

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers.config import Config
from helpers.auth import AuthHelper
from helpers.artifact_generator import ArtifactGenerator

# Shared PID pool: tier -> list[str]
_pids: dict[str, list[str]] = {tier: [] for tier in Config.ARTIFACT_SIZES}
_seed_lock = threading.Lock()
_seeded = False


def _seed_artifacts(host: str, auth: AuthHelper, count_per_tier: int = 3):
    """Upload a few artifacts per tier so download tasks have targets."""
    global _seeded
    if _seeded:
        return
    with _seed_lock:
        if _seeded:
            return
        for tier in Config.ARTIFACT_SIZES:
            filename, data = ArtifactGenerator.get(tier)
            for i in range(count_per_tier):
                # Step 1: get upload URL
                r = req.post(
                    f"{host}/artifacts/upload/url",
                    params={"filename": f"seed_{tier}_{i}.bin"},
                    headers=auth.headers,
                    timeout=Config.REQUEST_TIMEOUT,
                )
                if r.status_code not in (200, 201):
                    continue
                body = r.json()
                upload_url = body.get("upload_url") or body.get("url")
                pid = body.get("pid")
                if not upload_url or not pid:
                    continue

                # Make upload_url absolute if relative
                if upload_url.startswith("/"):
                    upload_url = f"{host}{upload_url}"

                # Step 2: PUT file
                files = {"file": (f"seed_{tier}_{i}.bin", io.BytesIO(data), "application/octet-stream")}
                r2 = req.put(upload_url, files=files, timeout=Config.REQUEST_TIMEOUT)
                if r2.status_code in (200, 201):
                    _pids[tier].append(pid)
        _seeded = True


class ArtifactDownloadUser(HttpUser):
    """Downloads artifacts via the presigned URL proxy flow."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed_artifacts(self.host, self.auth)

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

        # Step 1: get download URL
        with self.client.get(
            f"/artifacts/{pid}/download/url",
            name=f"artifact_get_download_url_{tier}",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}")
                return
            resp.success()
            body = resp.json()
            download_url = body.get("download_url") or body.get("url")
            if not download_url:
                resp.failure("No download_url in response")
                return

        # Step 2: GET the file from proxy
        with self.client.get(
            download_url,
            params={"stream": "true", "pid": pid},
            name=f"artifact_proxy_download_{tier}",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                _ = resp.content  # consume body
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
