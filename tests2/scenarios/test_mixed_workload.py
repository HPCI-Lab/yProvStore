"""
T8 — Mixed Workload
=====================
Simulates realistic concurrent usage with multiple operation types:
document upload/download, artifact upload/download, metadata reads,
and document listing — all running simultaneously.

Run example::

    locust -f scenarios/test_mixed_workload.py --headless \
           -u 50 -r 5 --run-time 10m \
           --csv=results/mixed_workload
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
from helpers.prov_generator import ProvGenerator
from helpers.artifact_generator import ArtifactGenerator

# ── Shared seed state ───────────────────────────────────────────────────────
_doc_pids: list[str] = []
_artifact_pids: list[str] = []
_payloads: dict[str, bytes] = {}
_artifact_data: dict[str, tuple[str, bytes]] = {}
_seed_lock = threading.Lock()
_seeded = False


def _seed(host: str, auth: AuthHelper):
    global _seeded
    if _seeded:
        return
    with _seed_lock:
        if _seeded:
            return

        # Seed documents (medium size)
        payload = ProvGenerator.get("medium")
        _payloads["medium"] = payload
        _payloads["small"] = ProvGenerator.get("small")

        for _ in range(10):
            files = {"document_file": ("seed.json", io.BytesIO(payload), "application/json")}
            r = req.post(f"{host}/documents", files=files, headers=auth.headers, timeout=Config.REQUEST_TIMEOUT)
            if r.status_code in (200, 201):
                pid = r.json().get("document_record", {}).get("pid") or r.json().get("pid")
                if pid:
                    _doc_pids.append(pid)

        # Seed artifacts (small)
        fname, data = ArtifactGenerator.get("small")
        _artifact_data["small"] = (fname, data)
        for i in range(5):
            r = req.post(
                f"{host}/artifacts/upload/url",
                params={"filename": f"seed_mixed_{i}.bin"},
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
            if upload_url.startswith("/"):
                upload_url = f"{host}{upload_url}"
            files = {"file": (f"seed_{i}.bin", io.BytesIO(data), "application/octet-stream")}
            r2 = req.put(upload_url, files=files, timeout=Config.REQUEST_TIMEOUT)
            if r2.status_code in (200, 201):
                _artifact_pids.append(pid)

        _seeded = True


# ── User classes ────────────────────────────────────────────────────────────

class DocumentWriter(HttpUser):
    """Uploads documents of varying sizes."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST
    weight = 2

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed(self.host, self.auth)

    @task
    def upload(self):
        tier = random.choice(["small", "medium"])
        payload = _payloads.get(tier) or ProvGenerator.get(tier)
        files = {"document_file": (f"doc_{tier}.json", io.BytesIO(payload), "application/json")}
        with self.client.post(
            "/documents", files=files, headers=self.auth.headers,
            name=f"mixed_upload_{tier}", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                pid = resp.json().get("document_record", {}).get("pid") or resp.json().get("pid")
                if pid:
                    _doc_pids.append(pid)
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class DocumentReader(HttpUser):
    """Downloads documents."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST
    weight = 5

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed(self.host, self.auth)

    @task
    def download(self):
        if not _doc_pids:
            return
        pid = random.choice(_doc_pids)
        with self.client.get(
            f"/documents/{pid}", params={"stream": "true"},
            name="mixed_download", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                _ = resp.content
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class ArtifactWriter(HttpUser):
    """Uploads artifacts via presigned URL proxy."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST
    weight = 1

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed(self.host, self.auth)

    @task
    def upload_artifact(self):
        fname, data = _artifact_data.get("small", ArtifactGenerator.get("small"))
        with self.client.post(
            "/artifacts/upload/url", params={"filename": f"mixed_{id(self)}.bin"},
            headers=self.auth.headers, name="mixed_artifact_url",
            timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"HTTP {resp.status_code}")
                return
            resp.success()
            body = resp.json()
            upload_url = body.get("upload_url") or body.get("url")
            pid = body.get("pid")
            if not upload_url:
                return

        files = {"file": (fname, io.BytesIO(data), "application/octet-stream")}
        with self.client.put(
            upload_url, files=files, name="mixed_artifact_upload",
            timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201):
                if pid:
                    _artifact_pids.append(pid)
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class ArtifactReader(HttpUser):
    """Downloads artifacts via presigned URL proxy."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST
    weight = 2

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed(self.host, self.auth)

    @task
    def download_artifact(self):
        if not _artifact_pids:
            return
        pid = random.choice(_artifact_pids)
        with self.client.get(
            f"/artifacts/{pid}/download/url", name="mixed_artifact_dl_url",
            timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}")
                return
            resp.success()
            dl_url = resp.json().get("download_url") or resp.json().get("url")
            if not dl_url:
                return

        with self.client.get(
            dl_url, params={"stream": "true", "pid": pid}, name="mixed_artifact_dl",
            timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                _ = resp.content
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class MetadataReader(HttpUser):
    """Reads document metadata."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST
    weight = 3

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed(self.host, self.auth)

    @task
    def read_metadata(self):
        if not _doc_pids:
            return
        pid = random.choice(_doc_pids)
        with self.client.get(
            f"/documents/{pid}/metadata", name="mixed_metadata_read",
            timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")


class DocumentLister(HttpUser):
    """Lists/paginates documents."""

    wait_time = between(Config.WAIT_TIME_MIN, Config.WAIT_TIME_MAX)
    host = Config.TARGET_HOST
    weight = 2

    def on_start(self):
        self.auth = AuthHelper(self.host)
        _seed(self.host, self.auth)

    @task
    def list_documents(self):
        page = random.randint(0, 5)
        with self.client.get(
            "/documents", params={"page": page, "page_size": 10},
            name="mixed_list_docs", timeout=Config.REQUEST_TIMEOUT, catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")
