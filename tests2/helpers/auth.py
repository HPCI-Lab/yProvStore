"""
Authentication helpers for performance tests.

Provides signup/login utilities and a shared token pool so Locust workers
can each operate as a distinct user without re-registering on every spawn.
"""

from __future__ import annotations

import itertools
import logging
import threading
from dataclasses import dataclass

import requests

from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class TestUser:
    email: str
    password: str
    token: str | None = None


# ── Module-level shared state (populated once, read by all greenlets) ────────
_users: list[TestUser] = []
_user_cycle: itertools.cycle | None = None
_lock = threading.Lock()
_initialized = False


def _signup(host: str, email: str, password: str) -> bool:
    """Register a user. Returns True if created or already exists."""
    try:
        r = requests.post(
            f"{host}/auth/signup",
            json={"email": email, "password": password},
            timeout=Config.REQUEST_TIMEOUT,
        )
        if r.status_code in (200, 201):
            return True
        if r.status_code == 409 or "already" in r.text.lower():
            return True  # user exists
        logger.warning("Signup failed for %s: %s %s", email, r.status_code, r.text)
        return False
    except Exception as exc:
        logger.error("Signup request error for %s: %s", email, exc)
        return False


def _login(host: str, email: str, password: str) -> str | None:
    """Login and return bearer token, or None on failure."""
    try:
        r = requests.post(
            f"{host}/auth/login",
            json={"email": email, "password": password},
            timeout=Config.REQUEST_TIMEOUT,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("access_token") or data.get("token")
        logger.warning("Login failed for %s: %s %s", email, r.status_code, r.text)
        return None
    except Exception as exc:
        logger.error("Login request error for %s: %s", email, exc)
        return None


def ensure_test_users(host: str | None = None, count: int | None = None) -> list[TestUser]:
    """Create *count* test users (signup + login) and cache their tokens.

    Safe to call from multiple greenlets — only the first caller does the work.
    Returns the full list of ``TestUser`` objects.
    """
    global _users, _user_cycle, _initialized

    if _initialized:
        return _users

    with _lock:
        if _initialized:
            return _users

        host = host or Config.TARGET_HOST
        count = count or Config.TEST_USER_COUNT

        logger.info("Registering %d test users on %s …", count, host)
        for n in range(count):
            email = Config.TEST_USER_EMAIL_TEMPLATE.format(n=n)
            password = Config.TEST_USER_PASSWORD

            _signup(host, email, password)
            token = _login(host, email, password)
            _users.append(TestUser(email=email, password=password, token=token))

        _user_cycle = itertools.cycle(_users)
        _initialized = True
        logger.info("Registered %d users (%d with valid tokens).",
                     len(_users), sum(1 for u in _users if u.token))
        return _users


def next_user() -> TestUser:
    """Return the next user from the round-robin pool (call ``ensure_test_users`` first)."""
    global _user_cycle
    if _user_cycle is None:
        ensure_test_users()
    assert _user_cycle is not None, "User pool not initialized"
    with _lock:
        return next(_user_cycle)


def auth_header(token: str) -> dict[str, str]:
    """Convenience: return an ``Authorization`` header dict."""
    return {"Authorization": f"Bearer {token}"}


class AuthHelper:
    """Stateful helper bound to one Locust user instance."""

    def __init__(self, host: str | None = None):
        self.host = host or Config.TARGET_HOST
        ensure_test_users(self.host)
        self._user = next_user()

    @property
    def email(self) -> str:
        return self._user.email

    @property
    def token(self) -> str | None:
        return self._user.token

    @property
    def headers(self) -> dict[str, str]:
        if self._user.token:
            return auth_header(self._user.token)
        return {}

    def refresh_token(self) -> None:
        """Re-login and update the cached token."""
        self._user.token = _login(self.host, self._user.email, self._user.password)
