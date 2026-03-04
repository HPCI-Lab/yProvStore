"""
Centralized configuration for all performance tests.

All values are overridable via environment variables.
"""

import os


class Config:
    """Test configuration loaded from environment variables with sensible defaults."""

    # ── Server ──────────────────────────────────────────────────────────────
    TARGET_HOST: str = os.getenv("TARGET_HOST", "http://localhost:8000")

    # ── Document sizes (bytes) ──────────────────────────────────────────────
    DOC_SIZES: dict[str, int] = {
        "small":  1_024,       # ~1 KB
        "medium": 65_536,      # ~64 KB
        "large":  1_048_576,   # ~1 MB
        "xlarge": 10_485_760,  # ~10 MB
    }

    # ── Artifact sizes (bytes) ──────────────────────────────────────────────
    ARTIFACT_SIZES: dict[str, int] = {
        "small":  1_024,
        "medium": 65_536,
        "large":  1_048_576,
        "xlarge": 10_485_760,
    }

    # ── Scalability sweep user counts ──────────────────────────────────────
    USER_COUNTS: list[int] = [
        int(x) for x in os.getenv("USER_COUNTS", "1,5,10,25,50,100,200").split(",")
    ]

    # ── Compression ─────────────────────────────────────────────────────────
    ZSTD_LEVEL: int = int(os.getenv("ZSTD_LEVEL", "1"))

    # ── Locust wait times (seconds) ─────────────────────────────────────────
    WAIT_TIME_MIN: float = float(os.getenv("WAIT_TIME_MIN", "0.2"))
    WAIT_TIME_MAX: float = float(os.getenv("WAIT_TIME_MAX", "0.5"))

    # ── Test users ──────────────────────────────────────────────────────────
    TEST_USER_EMAIL_TEMPLATE: str = "testuser_{n}@perftest.com"
    TEST_USER_PASSWORD: str = os.getenv("TEST_USER_PASSWORD", "PerfTest1234!")
    # Number of pre-registered users; each Locust worker picks one round-robin
    TEST_USER_COUNT: int = int(os.getenv("TEST_USER_COUNT", "50"))

    # ── Timeouts ────────────────────────────────────────────────────────────
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "120"))

    # ── Sustained / endurance test defaults ─────────────────────────────────
    SUSTAINED_RUN_TIME: str = os.getenv("SUSTAINED_RUN_TIME", "30m")
    SUSTAINED_USERS: int = int(os.getenv("SUSTAINED_USERS", "25"))

    # ── Paths ───────────────────────────────────────────────────────────────
    RESULTS_DIR: str = os.getenv("RESULTS_DIR", os.path.join(os.path.dirname(__file__), "..", "results"))
