"""
T5 — Artifact Upload Throughput
================================
Tests the full presigned-URL-based artifact upload flow under load:

1. POST ``/artifacts/upload/url?filename=…`` → get presigned upload URL + PID
2. PUT to the proxy upload URL with multipart file

Both steps are measured separately with distinct Locust request names.

Run example::

    locust -f scenarios/test_upload_artifacts.py --headless \
           -u 30 -r 5 --run-time 5m \
           --csv=results/upload_artifacts
"""

import io
import os
import sys
import random

from locust import HttpUser, task, between, events

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers.config import Config
from helpers.auth import AuthHelper
from helpers.artifact_generator import ArtifactGenerator

_artifacts: dict[str, tuple[str, bytes]] = {}


@events.test_start.add_listener
def _on_test_start(environment, **kwargs):
    for tier in Config.ARTIFACT_SIZES:
        _artifacts[tier] = ArtifactGenerator.get(tier)


class ArtifactUploadUser(HttpUser):
    """Performs the two-step artifact upload via presigned URL proxy."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST

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

    def _upload(self, tier: str):
        filename, data = _artifacts[tier]

        # Step 1: Get presigned upload URL
        with self.client.post(
            "/artifacts/upload/url",
            params={"filename": f"{filename}_{id(self)}"},
            headers=self.auth.headers,
            name=f"artifact_get_upload_url_{tier}",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"HTTP {resp.status_code}")
                return
            resp.success()
            body = resp.json()
            upload_url = body.get("upload_url") or body.get("url")
            pid = body.get("pid")
            if not upload_url:
                resp.failure("No upload_url in response")
                return

        # Step 2: PUT file to the proxy upload URL
        # The upload_url may be a relative path (/artifacts/proxy/upload/{token})
        # or absolute; Locust client handles relative paths against self.host.
        files = {"document_file": (filename, io.BytesIO(data), "application/octet-stream")}
        with self.client.put(
            upload_url,
            files=files,
            params={"pid": pid},
            name=f"artifact_proxy_upload_{tier}",
            timeout=Config.REQUEST_TIMEOUT,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
